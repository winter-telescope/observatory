"""
State Diagram Visualization for Custom State Machine

This module adds visualization capabilities to the custom state machine
implementation without requiring the transitions library.
"""

from enum import Enum
from typing import Dict, List, Optional, Set

import graphviz


class StateVisualizer:
    """
    Generate state diagrams for the custom state machine implementation.
    """

    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.graph = None

    def create_diagram(
        self,
        title: str = "Observatory State Machine",
        highlight_current: bool = True,
        show_conditions: bool = True,
        engine: str = "dot",
    ) -> graphviz.Digraph:
        """
        Create a state diagram from the state machine.

        Args:
            title: Title for the diagram
            highlight_current: Highlight current state in different color
            show_conditions: Show transition conditions on edges
            engine: Graphviz layout engine ('dot', 'neato', 'fdp', etc.)

        Returns:
            graphviz.Digraph object
        """
        # Create new directed graph
        self.graph = graphviz.Digraph(name=title, engine=engine)
        self.graph.attr(rankdir="TB", size="12,10")
        self.graph.attr(
            "node",
            shape="box",
            style="rounded,filled",
            fillcolor="lightblue",
            fontname="Arial",
        )
        self.graph.attr("edge", fontname="Arial", fontsize="10")

        # Add title
        self.graph.attr(label=title, fontsize="16", fontname="Arial Bold")

        # Define state transitions (manually from our implementation)
        transitions = self._get_transitions()

        # Add all states
        current_state = self.state_machine.context.current_state
        for state in self.state_machine.states.keys():
            attrs = {}

            # Highlight current state
            if highlight_current and state == current_state:
                attrs["fillcolor"] = "yellow"
                attrs["penwidth"] = "3"

            # Special styling for certain states
            if "ERROR" in state.name:
                attrs["fillcolor"] = "lightcoral"
            elif "IDLE" in state.name:
                attrs["fillcolor"] = "lightgreen"
            elif "STANDBY" in state.name:
                attrs["fillcolor"] = "lightgray"

            self.graph.node(state.name, **attrs)

        # Add transitions
        for source, dest, label in transitions:
            edge_attrs = {}
            if show_conditions and label:
                edge_attrs["label"] = label
            self.graph.edge(source, dest, **edge_attrs)

        return self.graph

    def _get_transitions(self) -> List[tuple]:
        """
        Define all possible state transitions.
        Returns list of (source, dest, condition_label) tuples.
        """
        # This maps our custom state machine logic to transitions
        # You'll need to update this based on your state machine implementation
        transitions = [
            # From IDLE
            ("IDLE", "CHECKING_CAMERAS", "running=True"),
            # Camera management
            ("CHECKING_CAMERAS", "STARTING_CAMERAS", "need startup"),
            ("CHECKING_CAMERAS", "CHECKING_CALS", "cameras ready"),
            ("CHECKING_CAMERAS", "SHUTTING_DOWN_CAMERAS", "should be off"),
            ("STARTING_CAMERAS", "WAITING_CAMERAS_READY", ""),
            ("WAITING_CAMERAS_READY", "CHECKING_CALS", "ready"),
            ("WAITING_CAMERAS_READY", "WAITING_CAMERAS_READY", "not ready"),
            # Calibration
            ("CHECKING_CALS", "EXECUTING_CAL", "cals needed"),
            ("CHECKING_CALS", "CHECKING_CONDITIONS", "no cals"),
            ("EXECUTING_CAL", "EXECUTING_CAL", "more cals"),
            ("EXECUTING_CAL", "CHECKING_CONDITIONS", "done"),
            # Conditions
            ("CHECKING_CONDITIONS", "STOWING", "bad weather"),
            ("CHECKING_CONDITIONS", "STANDBY", "sun high"),
            ("CHECKING_CONDITIONS", "OPENING_DOME", "dome closed"),
            ("CHECKING_CONDITIONS", "CHECKING_FOCUS", "all good"),
            # Focus
            ("CHECKING_FOCUS", "EXECUTING_FOCUS", "need focus"),
            ("CHECKING_FOCUS", "SELECTING_TARGET", "focus ok"),
            ("EXECUTING_FOCUS", "STANDBY", ""),
            # Observations
            ("SELECTING_TARGET", "SWITCHING_PORT", "found target"),
            ("SELECTING_TARGET", "STANDBY", "no targets"),
            ("SELECTING_TARGET", "END_OF_SCHEDULE", "schedule done"),
            ("SWITCHING_PORT", "PREPARING_OBSERVATION", "port ready"),
            ("SWITCHING_PORT", "STANDBY", "switching"),
            ("PREPARING_OBSERVATION", "OBSERVING", ""),
            ("OBSERVING", "CHECKING_CAMERAS", "complete"),
            # Standby returns
            ("STANDBY", "IDLE", "timer"),
            # Error can come from anywhere
            ("CHECKING_CAMERAS", "ERROR", "error"),
            ("STARTING_CAMERAS", "ERROR", "error"),
            ("EXECUTING_CAL", "ERROR", "error"),
            ("OBSERVING", "ERROR", "error"),
            ("ERROR", "STANDBY", "recover"),
            # Stowing
            ("STOWING", "STANDBY", ""),
            # Shutdown sequence
            ("SHUTTING_DOWN_CAMERAS", "CAMERA_POWEROFF", "shutdown complete"),
            ("SHUTTING_DOWN_CAMERAS", "STANDBY", "waiting"),
            ("CAMERA_POWEROFF", "STOWING", ""),
            ("END_OF_SCHEDULE", "STANDBY", ""),
        ]

        return transitions

    def save(
        self,
        filename: str = "state_diagram",
        format: str = "png",
        view: bool = False,
        **kwargs,
    ):
        """
        Save the state diagram to a file.

        Args:
            filename: Output filename (without extension)
            format: Output format ('png', 'pdf', 'svg', 'dot')
            view: Open the file after saving
            **kwargs: Additional arguments for create_diagram
        """
        if self.graph is None:
            self.create_diagram(**kwargs)

        # Render the graph
        self.graph.render(filename, format=format, cleanup=True, view=view)
        print(f"State diagram saved to {filename}.{format}")

    def get_dot_source(self) -> str:
        """Get the DOT source code for the graph."""
        if self.graph is None:
            self.create_diagram()
        return self.graph.source


# Add this method to your MultiCameraStateMachine class:
def visualize_state_machine(
    state_machine, filename="observatory_states", format="png", view=False
):
    """
    Standalone function to visualize a state machine.

    Args:
        state_machine: The MultiCameraStateMachine instance
        filename: Output filename
        format: Output format
        view: Whether to open the file after creation
    """
    visualizer = StateVisualizer(state_machine)
    visualizer.create_diagram(
        title="Multi-Camera Observatory State Machine",
        highlight_current=True,
        show_conditions=True,
    )
    visualizer.save(filename, format=format, view=view)


# Example usage showing both approaches
if __name__ == "__main__":
    print("Comparison of visualization approaches:")
    print("\n1. TRANSITIONS LIBRARY:")
    print("   - Automatic from state machine definition")
    print("   - Updates dynamically as states change")
    print("   - Built-in support for nested/parallel states")
    print("   - Can show transition conditions automatically")
    print("   - Requires transitions library + pygraphviz/graphviz")

    print("\n2. CUSTOM VISUALIZATION:")
    print("   - Requires manual transition mapping")
    print("   - More control over appearance")
    print("   - Only requires graphviz")
    print("   - Can customize for your specific needs")
    print("   - Need to update when state machine changes")

    # Create comparison diagram
    comparison_graph = graphviz.Digraph("comparison")
    comparison_graph.attr(rankdir="LR")

    # Transitions approach
    with comparison_graph.subgraph(name="cluster_0") as c:
        c.attr(label="Transitions Library", style="filled", color="lightgrey")
        c.node("T1", "Define states & transitions")
        c.node("T2", "Automatic diagram")
        c.edge("T1", "T2", "get_graph()")

    # Custom approach
    with comparison_graph.subgraph(name="cluster_1") as c:
        c.attr(label="Custom Visualization", style="filled", color="lightblue")
        c.node("C1", "Define states")
        c.node("C2", "Map transitions")
        c.node("C3", "Generate diagram")
        c.edge("C1", "C2")
        c.edge("C2", "C3", "graphviz")

    comparison_graph.render("visualization_comparison", format="png", cleanup=True)
