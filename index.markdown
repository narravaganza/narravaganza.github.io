---
title: Short Stories
layout: default
---
# Short Stories for your online reading delight

Hello, thanks for dropping by, here are some short stories I wrote for you to enjoy.

{% for story in site.stories %}
### [{{ story.name }}]({{story.url}})
#### {{ story.preview }}
{% endfor %}


