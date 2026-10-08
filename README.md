# Humasure Newsroom

Story files for Humasure News (humasure.org/news/). The newsroom agent adds one JSON file per story to `posts/`. The Humasure Site plugin on humasure.org checks this repository every hour and turns new files into posts:

- Explainers, guides and Humasure updates that name no company: published automatically (if enabled).
- News, analysis, and anything naming a company or person: saved as **Pending** in WordPress until a person reviews and publishes it.

`AGENT.md` holds the agent's standing instructions (sources, writing rules, brand rules, file format).

Changing a file that is already published does nothing; edit live posts in WordPress.
