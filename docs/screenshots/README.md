# Modern Windows Qt UI

All samples are synthetic and use isolated configuration. These maintained
documentation samples and regression baselines are rendered offscreen.
They do not contain real passwords or user documents.

| Sample | Purpose |
| --- | --- |
| minimal-text-zh-CN.png | Text idle baseline, 1024 x 760 |
| minimal-file-zh-CN.png | File idle baseline, 1024 x 760 |
| minimal-base64-zh-CN.png | Base64 idle baseline, 1024 x 760 |
| basic-text-result.png | Input and result share space; result actions remain visible |
| basic-settings.png | Appearance and language settings, collapsed advanced options |

These images describe the 1.2.0 interface. The implementation uses styled Qt Widgets
and a system title bar, not WinUI.

Retired recovery UI is no longer part of the product; its former sample is
removed from the current documentation (Git history is retained).

Temporary Windows validation screenshots, stress-DPI samples and raw logs are
generated separately and are not part of the maintained screenshot set.
See [UI_SPEC.md](../UI_SPEC.md) for regeneration and behavior-test commands.
