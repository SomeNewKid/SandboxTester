"""A reorter for printing results."""

from typing import Protocol

from .models import InvocationResult


class TestReporter(Protocol):
    def group_started(self, group_id: str, group_title: str) -> None: ...

    def capability_started(self, capability_id: str, capability_title: str) -> None: ...

    def shell_completed(self, result: InvocationResult) -> None: ...

    def tool_completed(self, result: InvocationResult) -> None: ...


class ConsoleReporter:
    def group_started(self, group_id: str, group_title: str) -> None:
        print()
        print(f"{group_id} {group_title}")
        print("-" * 20)

    def capability_started(self, capability_id: str, capability_title: str) -> None:
        print(f"{capability_id} {capability_title}")

    def shell_completed(self, result: InvocationResult) -> None:
        print(f"  shell: {result.outcome}")

    def tool_completed(self, result: InvocationResult) -> None:
        print(f"  tool:  {result.outcome}")


class QuietReporter:
    def group_started(self, group_id: str, group_title: str) -> None:
        # the suite is too long running to not print anything.
        print(f"{group_id} {group_title}")

    def capability_started(self, capability_id: str, capability_title: str) -> None:
        pass

    def shell_completed(self, result: InvocationResult) -> None:
        pass

    def tool_completed(self, result: InvocationResult) -> None:
        pass
