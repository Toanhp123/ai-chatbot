# Commands and Structured Workflows

## 1. Principle

User-facing slash commands are shortcuts to structured application actions. They must not be implemented as fragile hidden prompt strings when the action has real application semantics.

Initial candidate commands preserved from the original product design:

- `/model` — inspect/change model or route;
- `/agent` — inspect/change active agent configuration;
- `/plan` — enter the product's planning workflow for the current task;
- `/compact` — request context compaction;
- `/clear` — clear/reset the current conversation according to explicit semantics;
- `/context` — inspect context budget/sources;
- `/skills` — inspect/enable relevant Skills;
- `/mcp` — inspect/configure MCP servers/tools;
- `/diff` — open current task/workspace diff;
- `/checkpoint` — inspect/create/restore task checkpoint;
- `/project` — inspect/change active Project.

Do not ship commands before their underlying structured action exists.

## 2. Command registry

Conceptual command descriptor:

```ts
interface CommandDefinition {
  id: string;
  name: string;
  description: string;
  argumentSchema?: JsonSchema;
  availability: CommandAvailability;
  actionId: string;
  provenance: 'builtin' | 'plugin';
}
```

The command parser resolves syntax and arguments, then dispatches an application action. It should not concatenate the command text into a system prompt as the primary implementation.

## 3. Plugin commands

Plugins may register **command descriptors** through the extension manifest/registry. The descriptor resolves to an approved application action/use case; it is subject to the plugin revision active in that scope and normal runtime policy, and cannot register an arbitrary privileged in-process callback.

## 4. Product modes

Read-only investigation, planning, and authorized action are product workflow modes, not instructions for the external coding agent developing this repository.

Mode changes should alter:

- available tools;
- permission defaults;
- UI state;
- task policy;

rather than only changing prompt wording.

## 5. Workflow actions

Prefer composable action IDs for operations such as:

- `conversation.new`;
- `conversation.compact`;
- `project.switch`;
- `model.select`;
- `route.select`;
- `agent.select`;
- `task.plan`;
- `diff.open`;
- `checkpoint.restore`;
- `mcp.manage`;
- `skills.manage`.

This makes keyboard shortcuts, command palette, slash commands and future automation share the same business logic.
