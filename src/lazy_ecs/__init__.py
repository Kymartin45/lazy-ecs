import boto3
from rich.console import Console

from .aws_service import ECSService, TaskDetails
from .ui import ECSNavigator

console = Console()


def main() -> None:
    """Interactive AWS ECS navigation tool."""
    console.print("🚀 Welcome to lazy-ecs!", style="bold cyan")
    console.print("Interactive AWS ECS cluster navigator\n", style="dim")

    try:
        # Initialize AWS ECS client and service layer
        ecs_client = boto3.client("ecs")
        ecs_service = ECSService(ecs_client)
        navigator = ECSNavigator(ecs_service)

        # Start hierarchical navigation
        _navigate_clusters(navigator, ecs_service)

    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")
        console.print("Make sure your AWS credentials are configured.", style="dim")


def _navigate_clusters(navigator: ECSNavigator, ecs_service: ECSService) -> None:
    """Handle cluster-level navigation with back support."""
    while True:
        selected_cluster = navigator.select_cluster()

        if not selected_cluster:
            console.print("\n❌ No cluster selected. Goodbye!", style="yellow")
            break

        console.print(f"\n✅ Selected cluster: {selected_cluster}", style="green")

        # Navigate to services, handle back navigation
        if _navigate_services(navigator, ecs_service, selected_cluster):
            continue  # Back to cluster selection
        break  # Exit was chosen


def _navigate_services(navigator: ECSNavigator, ecs_service: ECSService, cluster_name: str) -> bool:
    """Handle service-level navigation. Returns True if back was chosen, False if exit."""
    selected_service = navigator.select_service(cluster_name)

    if not selected_service:
        console.print(
            f"\n❌ No service selected from '{cluster_name}'. Going back to cluster selection.", style="yellow"
        )
        return True

    console.print(f"\n✅ Selected service: {selected_service}", style="green")

    while True:
        selection = navigator.select_service_action(cluster_name, selected_service)

        if not selection or selection["value"] == "exit":
            console.print("\n👋 Goodbye!", style="cyan")
            return False

        if selection["value"] == "back":
            return True  # Back to cluster selection

        if selection["type"] == "task":
            selected_task = selection["value"]
            task_details = ecs_service.get_task_details(cluster_name, selected_service, selected_task)
            if task_details:
                navigator.display_task_details(task_details)
                # Navigate to task features, handle back navigation
                if _handle_task_features(navigator, cluster_name, selected_task, task_details):
                    continue  # Back to service selection
                return False  # Exit was chosen
            console.print(f"\n⚠️ Could not fetch task details for {selected_task}", style="yellow")

        elif selection["type"] == "action" and selection["value"] == "force_deployment":
            navigator.handle_force_deployment(cluster_name, selected_service)
            # Continue the loop to show the menu again


def _handle_task_features(
    navigator: ECSNavigator, cluster_name: str, task_arn: str, task_details: TaskDetails | None
) -> bool:
    """Handle task feature selection and execution. Returns True if back was chosen, False if exit."""
    while True:
        selection = navigator.select_task_feature(task_details)

        if not selection:
            console.print("\n👋 Goodbye!", style="cyan")
            return False

        if selection["type"] == "navigation":
            if selection["value"] == "exit":
                console.print("\n👋 Goodbye!", style="cyan")
                return False
            if selection["value"] == "back":
                return True

        elif selection["type"] == "container_action":
            container_name = selection["container"]
            action_name = selection["action"]

            # Map action names to methods
            action_methods = {
                "show_logs": navigator.show_container_logs,
                "show_env": navigator.show_container_environment_variables,
                "show_secrets": navigator.show_container_secrets,
                "show_ports": navigator.show_container_port_mappings,
            }

            if action_name in action_methods:
                action_methods[action_name](cluster_name, task_arn, container_name)


if __name__ == "__main__":
    main()
