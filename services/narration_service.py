
from core.narration_models import NarrationInput, NarrationResult


class NarrationService:

    def generate(self, data: NarrationInput) -> NarrationResult:

        lines = []

        if data.action_type == "move":
            lines.append(f"A csapat belép: {data.room_title}")

        elif data.action_type == "failed_move":
            lines.append("A csapat megakad.")

        if data.exit_reason == "locked_no_solution":
            lines.append("Az ajtó zárva van.")

        if data.exit_reason == "lockpick_failed":
            lines.append("A zár ellenáll.")

        if data.exit_reason == "strength_failed":
            lines.append("Nem tudjátok betörni.")

        if data.trap_triggered:
            for trap in data.trap_names:
                lines.append(f"Csapda aktiválódik: {trap}")

        if data.combat_triggered:
            lines.append("Harci helyzet alakul ki!")

        if data.room_facts:
            lines.append(data.room_facts[:200])

        return NarrationResult("\n".join(lines))
