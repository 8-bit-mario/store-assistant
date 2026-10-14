# ABOUTME: User-message template carrying recorded actions and end reason to the summary call.
# ABOUTME: Filled with str.format: {actions}, {end_reason} and {end_reason_text}.

SUMMARY_REQUEST_TEMPLATE = """\
<actions>
{actions}
</actions>

<end_reason>
{end_reason}: {end_reason_text}
</end_reason>
"""
