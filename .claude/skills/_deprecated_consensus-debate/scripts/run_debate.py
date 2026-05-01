#!/usr/bin/env python3
"""多模型共识博弈脚本 - 三阶段：提案 → 交叉评审 → Judge 汇总。"""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import httpx


@dataclass(frozen=True)
class ModelConfig:
    name: str
    endpoint: str
    api_key: str
    model: str
    role: str = "participant"
    protocol: str = "openai"  # "openai" 或 "anthropic"


class ModelClient:
    def __init__(self, config: ModelConfig, timeout: float = 300.0):
        self.config = config
        self.timeout = timeout

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        if self.config.protocol == "anthropic":
            return await self._chat_anthropic(system_prompt, user_prompt)
        return await self._chat_openai(system_prompt, user_prompt)

    async def _chat_openai(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "max_tokens": 16384,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            print(f"[consensus-engine] 请求 {self.config.name} (openai)...", file=sys.stderr)
            resp = await http.post(self.config.endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(f"[consensus-engine] {self.config.name} 响应完成", file=sys.stderr)
            return content

    async def _chat_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            print(f"[consensus-engine] 请求 {self.config.name} (anthropic)...", file=sys.stderr)
            url = self.config.endpoint.rstrip("/")
            if not url.endswith("/messages"):
                url += "/messages"
            resp = await http.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            print(f"[consensus-engine] {self.config.name} 响应完成", file=sys.stderr)
            return content


def _find_models_json() -> Optional[Path]:
    """查找 models.json：先找脚本同级目录，再fallback环境变量。"""
    script_dir = Path(__file__).resolve().parent
    sibling = script_dir / "models.json"
    if sibling.exists():
        return sibling
    return None


def load_model_configs() -> list[ModelConfig]:
    config_path = _find_models_json()
    if config_path:
        raw = config_path.read_text(encoding="utf-8")
        source = f"文件 {config_path}"
    else:
        raw = os.environ.get("LOCAL_MODEL_CONFIGS")
        source = "环境变量 LOCAL_MODEL_CONFIGS"

    if not raw:
        print(
            "[consensus-engine] 错误：未找到模型配置。\n"
            "请在 skill 同级目录放置 models.json，或设置 LOCAL_MODEL_CONFIGS 环境变量。\n"
            "格式为 JSON 数组，例如：\n"
            '[{"name":"gpt-4o","endpoint":"...","api_key":"...","model":"gpt-4o","role":"judge"}]',
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"{source} JSON 解析失败：{e}")

    required_fields = {"name", "endpoint", "api_key", "model"}
    configs = []
    for item in items:
        missing = required_fields - set(item.keys())
        if missing:
            raise ValueError(f"模型配置缺少必填字段：{missing}（模型：{item.get('name', '?')}）")
        configs.append(
            ModelConfig(
                name=item["name"],
                endpoint=item["endpoint"],
                api_key=item["api_key"],
                model=item["model"],
                role=item.get("role", "participant"),
                protocol=item.get("protocol", "openai"),
            )
        )

    if len(configs) < 2:
        raise ValueError("至少需要 2 个模型配置")

    judges = [c for c in configs if c.role == "judge"]
    if len(judges) != 1:
        raise ValueError(f"恰好需要 1 个 judge 模型，当前有 {len(judges)} 个")

    return configs


# === Prompt Templates ===

def build_proposal_prompt(task: str, content: str, scene: str) -> tuple[str, str]:
    system = (
        "你是一位资深技术专家。请根据任务描述和上下文，"
        "提出你的详细方案。要求结构清晰、可执行。"
    )
    user = (
        f"## 任务\n{task}\n\n"
        f"## 上下文\n{content}\n\n"
        f"## 场景\n{scene}\n\n"
        "请输出你的完整方案（Markdown 格式）。"
    )
    return system, user


def build_review_prompt(task: str, proposals: dict[str, str]) -> tuple[str, str]:
    system = (
        "你是一位严谨的技术评审专家。"
        "请对以下方案进行批判性评审，指出漏洞、安全风险或性能瓶颈。"
    )
    proposals_text = "\n\n".join(
        f"### {name} 的方案\n{text}" for name, text in proposals.items()
    )
    user = (
        f"## 任务\n{task}\n\n"
        f"## 各专家提案\n{proposals_text}\n\n"
        "请逐一评审以上方案，指出问题并给出改进建议。"
    )
    return system, user


def build_synthesis_prompt(
    task: str, proposals: dict[str, str], reviews: dict[str, str]
) -> tuple[str, str]:
    system = (
        "你是最终裁判。综合所有专家的提案和评审意见，"
        "输出一份结构化的最终共识方案（Markdown 格式）。"
    )
    proposals_text = "\n\n".join(
        f"### {name} 的方案\n{text}" for name, text in proposals.items()
    )
    reviews_text = "\n\n".join(
        f"### {name} 的评审\n{text}" for name, text in reviews.items()
    )
    user = (
        f"## 任务\n{task}\n\n"
        f"## 原始提案\n{proposals_text}\n\n"
        f"## 评审意见\n{reviews_text}\n\n"
        "请输出最终共识方案。"
    )
    return system, user


# === Orchestrator ===

@dataclass
class DebateResult:
    final_plan: str
    models_participated: list[str]
    models_failed: list[str]
    model_mapping: dict[str, str] = field(default_factory=dict)
    proposals: dict[str, str] = field(default_factory=dict)
    reviews: dict[str, str] = field(default_factory=dict)


async def _safe_chat(
    name: str, client: ModelClient, system: str, user: str
) -> tuple[str, Optional[str]]:
    try:
        result = await client.chat(system, user)
        return name, result
    except Exception as e:
        import traceback
        print(f"[consensus-engine] {name} 失败：{e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return name, None


async def run_debate(
    configs: list[ModelConfig],
    task: str,
    content: str,
    scene: str,
    review_mode: str = "summarized",
) -> DebateResult:
    judge_config = next(c for c in configs if c.role == "judge")
    participant_configs = [c for c in configs if c.role != "judge"]

    all_debaters = [judge_config] + participant_configs
    clients = {c.name: ModelClient(c) for c in all_debaters}

    failed: list[str] = []

    # Phase 1: Proposal
    print(
        f"[Phase 1/3] 向 {len(all_debaters)} 个模型请求提案...", file=sys.stderr
    )
    system_p, user_p = build_proposal_prompt(task, content, scene)
    tasks_p = [
        _safe_chat(c.name, clients[c.name], system_p, user_p) for c in all_debaters
    ]
    results_p = await asyncio.gather(*tasks_p)

    proposals: dict[str, str] = {}
    for name, result in results_p:
        if result is None:
            failed.append(name)
        else:
            proposals[name] = result

    if len(proposals) < 2:
        raise RuntimeError(
            f"提案阶段成功模型不足 2 个（成功：{list(proposals.keys())}）"
        )

    # Phase 2: Cross-Review
    print(
        f"[Phase 2/3] 交叉评审中（{review_mode} 模式）...", file=sys.stderr
    )
    reviews: dict[str, str] = {}

    if review_mode == "full":
        review_tasks = []
        for reviewer_name, client in clients.items():
            if reviewer_name in failed:
                continue
            other_proposals = {
                k: v for k, v in proposals.items() if k != reviewer_name
            }
            if not other_proposals:
                continue
            system_r, user_r = build_review_prompt(task, other_proposals)
            review_tasks.append(_safe_chat(reviewer_name, client, system_r, user_r))

        results_r = await asyncio.gather(*review_tasks)
        for name, result in results_r:
            if result is None:
                if name not in failed:
                    failed.append(name)
            else:
                reviews[name] = result
    else:
        system_r, user_r = build_review_prompt(task, proposals)
        review_tasks = [
            _safe_chat(name, clients[name], system_r, user_r)
            for name in proposals
            if name not in failed
        ]
        results_r = await asyncio.gather(*review_tasks)
        for name, result in results_r:
            if result is None:
                if name not in failed:
                    failed.append(name)
            else:
                reviews[name] = result

    # Phase 3: Synthesis
    print(
        f"[Phase 3/3] Judge ({judge_config.name}) 汇总共识...", file=sys.stderr
    )
    system_s, user_s = build_synthesis_prompt(task, proposals, reviews)
    judge_client = clients[judge_config.name]
    _, synthesis = await _safe_chat(judge_config.name, judge_client, system_s, user_s)

    if synthesis is None:
        raise RuntimeError("Judge 模型汇总失败（可能在之前阶段已失败）")

    participated_names = [n for n in [c.name for c in all_debaters] if n not in failed]
    model_mapping = {c.name: c.model for c in all_debaters if c.name in participated_names}

    return DebateResult(
        final_plan=synthesis,
        models_participated=participated_names,
        models_failed=failed,
        model_mapping=model_mapping,
        proposals=proposals,
        reviews=reviews,
    )


# === Markdown Writer ===

SCENE_DIR_MAP: dict[str, str] = {
    "planning": "plan",
    "review": "codereview",
    "arch": "arch",
    "debug": "debug",
}


def write_markdown(
    result: DebateResult, task: str, scene: str, project_root: Optional[Path] = None
) -> Optional[Path]:
    if scene not in SCENE_DIR_MAP:
        return None
    subdir = SCENE_DIR_MAP[scene]
    root = project_root or Path.cwd()
    target_dir = root / "docs" / "consensus-debate" / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    filename = f"{now.strftime('%Y%m%d_%H%M')}_{scene}.md"
    filepath = target_dir / filename

    proposals_section = "\n".join(
        f"- **{name}** (`{result.model_mapping.get(name, '?')}`): {text[:200]}..."
        if len(text) > 200
        else f"- **{name}** (`{result.model_mapping.get(name, '?')}`): {text}"
        for name, text in result.proposals.items()
    )
    reviews_section = "\n".join(
        f"- **{name}** (`{result.model_mapping.get(name, '?')}`): {text[:200]}..."
        if len(text) > 200
        else f"- **{name}** (`{result.model_mapping.get(name, '?')}`): {text}"
        for name, text in result.reviews.items()
    )

    model_lines = "\n".join(
        f"- {name} (`{result.model_mapping.get(name, '?')}`)"
        for name in result.models_participated
    )
    md = (
        f"# 共识结论：{task}\n\n"
        f"> 场景：{scene} | 时间：{now.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"## 最终方案\n\n{result.final_plan}\n\n"
        f"## 参与模型\n\n{model_lines}\n\n"
        f"## 博弈摘要\n\n"
        f"### 提案阶段\n{proposals_section}\n\n"
        f"### 评审阶段\n{reviews_section}\n"
    )
    filepath.write_text(md, encoding="utf-8")
    return filepath


# === CLI ===

def main() -> None:
    parser = argparse.ArgumentParser(description="运行多模型共识博弈")
    parser.add_argument("--task", required=True, help="核心任务描述")
    parser.add_argument("--content", default="", help="相关代码或上下文")
    parser.add_argument(
        "--scene",
        required=True,
        choices=["planning", "review", "arch", "debug"],
        help="场景类型",
    )
    parser.add_argument(
        "--review-mode",
        default="summarized",
        choices=["summarized", "full"],
        help="评审模式",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="将结果保存为 Markdown 文件到 docs/ 下",
    )
    args = parser.parse_args()

    configs = load_model_configs()
    result = asyncio.run(
        run_debate(
            configs=configs,
            task=args.task,
            content=args.content,
            scene=args.scene,
            review_mode=args.review_mode,
        )
    )

    output = {
        "final_plan": result.final_plan,
        "models_participated": result.models_participated,
        "models_failed": result.models_failed,
        "model_mapping": result.model_mapping,
        "proposals": result.proposals,
        "reviews": result.reviews,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if args.save:
        root = Path(os.environ.get("PROJECT_ROOT", "."))
        filepath = write_markdown(result, args.task, args.scene, root)
        if filepath:
            print(f"[consensus-engine] 已保存：{filepath}", file=sys.stderr)


if __name__ == "__main__":
    main()
