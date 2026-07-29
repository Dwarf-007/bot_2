# F2.5 – CharacterCreationAdvisor Aggregate Gate Architecture

## Role

```text
F2.2 CharacterCreationSmokeGate
F2.4 CharacterCreationRuntimeWiringSmoke
Application TurnOutput contract check
Runtime coupling scan
    -> CharacterCreationAggregateGate
```

## TurnOutput contract

F2 aggregate verifies:

```text
public_narrative contains advisory content
suggested_commands == []
avrae_commands == []
dm_instructions present
```

## Runtime coupling scan

Forbidden markers:

```text
dispatch_commands
AvraeDispatcher(
AvraeClient(
.is_available()
message.channel.send
```

## Closure

Passing this gate means the F2 CharacterCreationAdvisor MVP is stable enough to be used as an advisory runtime capability.
