import re

# Read the file
with open('c:\\Users\\abbak\\Posdoll\\tracker\\views.py', 'r') as f:
    content = f.read()

# Fix the indentation error
fixed_content = re.sub(
    r'(if period == "daily":\n\s*)$',
    'if period == "daily":\n            f_from = f_to = today.isoformat()\n        elif period == "weekly":\n            f_from = (today - timedelta(days=today.weekday())).isoformat()  # Start of current week\n            f_to = today.isoformat()\n        elif period == "monthly":\n            f_from = today.replace(day=1).isoformat()  # Start of current month\n            f_to = today.isoformat()\n        elif period == "yearly":\n            f_from = today.replace(month=1, day=1).isoformat()  # Start of current year\n            f_to = today.isoformat()',
    content,
    flags=re.MULTILINE
)

# Write the fixed content back to the file
with open('c:\\Users\\abbak\\Posdoll\\tracker\\views.py', 'w') as f:
    f.write(fixed_content)
