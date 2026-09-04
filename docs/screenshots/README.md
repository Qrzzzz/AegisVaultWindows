# Basic light Qt UI

All samples are synthetic, rendered offscreen with isolated configuration.
They do not contain real passwords or user documents.

| Sample | Purpose |
| --- | --- |
| minimal-text-zh-CN.png | Text idle baseline, 900 x 680 |
| minimal-file-zh-CN.png | File idle baseline, 900 x 680 |
| minimal-base64-zh-CN.png | Base64 idle baseline, 900 x 680 |
| basic-text-result.png | Input and result share space; result actions remain visible |
| basic-settings.png | Native form, no theme selector, collapsed dangerous options |

Retired recovery UI is no longer part of the product; its former sample is
removed from the current documentation (Git history is retained).

English, small-window, high-DPI, file-result, advanced and error screenshots
belong in the task's external QA directory, not in the committed baseline set.
See [UI_SPEC.md](../UI_SPEC.md) for regeneration and behavior-test commands.
