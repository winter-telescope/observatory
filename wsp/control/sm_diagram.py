# sm_diagram.py
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set


@dataclass(frozen=True)
class Edge:
    src: Enum
    dst: Enum
    label: Optional[str] = None


class GraphRecorder:
    def __init__(self, sm):
        self.sm = sm
        self.edges: Set[Edge] = set()
        self.seen_states: Set[Enum] = set()
        self.start_node = "start"
        self.initial_state = sm.context.current_state

    def record(self, src, dst, label: Optional[str]):
        self.seen_states.add(src)
        self.seen_states.add(dst)
        self.edges.add(Edge(src, dst, label))

    def _all_states(self) -> List[Enum]:
        enum_cls = type(self.sm.context.current_state)
        return list(enum_cls)

    def _implemented_states(self) -> Set[Enum]:
        return set(self.sm.states.keys())

    def export_dot(self, path: str):
        enum_cls = type(self.sm.context.current_state)
        all_states = self._all_states()
        implemented = self._implemented_states()
        placeholders = [s for s in all_states if s not in implemented]

        lines = []
        lines.append("digraph MultiCameraSM {")
        lines.append("  rankdir=LR;")
        lines.append('  labelloc="t";')
        lines.append('  label="Multi-Camera Robo Operator — State Machine (observed)";')
        lines.append(
            '  node [shape=ellipse, style=filled, fillcolor="#eaffea", color="#2a7a2a", fontsize=11];'
        )
        for s in implemented:
            lines.append(f"  {s.name};")
        if placeholders:
            lines.append(
                '  node [style="dashed,filled", fillcolor="#f0f0f0", color="#777777"];'
            )
            for s in placeholders:
                lines.append(f"  {s.name};")
        lines.append('  edge [fontsize=9, color="#555555"];')
        lines.append(
            f'  {self.start_node} [shape=point, width=0.08, label="", color="#444444"];'
        )
        lines.append(f"  {self.start_node} -> {self.initial_state.name};")
        for e in sorted(
            self.edges, key=lambda x: (x.src.name, x.dst.name, x.label or "")
        ):
            if e.label:
                lbl = e.label.replace('"', '\\"')
                lines.append(f'  {e.src.name} -> {e.dst.name} [label="{lbl}"];')
            else:
                lines.append(f"  {e.src.name} -> {e.dst.name};")
        lines.append("}")
        Path(path).write_text("\n".join(lines), encoding="utf-8")

    def export_mermaid(self, path: str):
        """Write a Mermaid stateDiagram-v2."""
        enum_cls = type(self.sm.context.current_state)
        all_states = self._all_states()
        implemented = self._implemented_states()
        placeholders = [s for s in all_states if s not in implemented]

        lines = []
        lines.append("stateDiagram-v2")
        # Start pointer
        lines.append(f"  [*] --> {self.initial_state.name}")
        # We don't need to declare states explicitly; Mermaid infers nodes from edges.

        for e in sorted(
            self.edges, key=lambda x: (x.src.name, x.dst.name, x.label or "")
        ):
            if e.label:
                lbl = e.label.replace('"', '\\"')
                lines.append(f"  {e.src.name} --> {e.dst.name}: {lbl}")
            else:
                lines.append(f"  {e.src.name} --> {e.dst.name}")

        # Optionally annotate placeholders (as notes)
        for s in placeholders:
            lines.append(f"  note right of {s.name}: placeholder (no handler)")

        Path(path).write_text("\n".join(lines), encoding="utf-8")

    def inject_mermaid_into_markdown(
        self, md_path: str, fence_begin="<!-- SM:BEGIN -->", fence_end="<!-- SM:END -->"
    ):
        """Replace a fenced section in markdown with the current Mermaid diagram."""
        mermaid_code = []
        mermaid_code.append("```mermaid")
        mermaid_code.append(
            Path("diagrams/multicamera_sm.mmd").read_text(encoding="utf-8")
        )
        mermaid_code.append("```")
        mermaid_block = "\n".join(mermaid_code)

        p = Path(md_path)
        if not p.exists():
            # Create a basic doc with fences
            p.write_text(
                f"# State Machine\n\n{fence_begin}\n{mermaid_block}\n{fence_end}\n",
                encoding="utf-8",
            )
            return

        text = p.read_text(encoding="utf-8")
        if fence_begin in text and fence_end in text:
            before = text.split(fence_begin)[0]
            after = text.split(fence_end)[1]
            new_text = f"{before}{fence_begin}\n{mermaid_block}\n{fence_end}{after}"
        else:
            # Append fenced block if not present
            new_text = text + f"\n\n{fence_begin}\n{mermaid_block}\n{fence_end}\n"
        p.write_text(new_text, encoding="utf-8")


def label_next_transition(context, label: str):
    context.state_data["_transition_label"] = label
