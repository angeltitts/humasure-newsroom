# Instagram auto-posting

The Instagram workflow (`.github/workflows/instagram.yml`) runs at about 9:30am and 5:30pm Pacific. Each run:

1. Makes cards for any story that has none (`tools/social_cards.py --missing`).
2. Posts **one** story to @humasureai as a 3-slide carousel (`tools/instagram_post.py`).

## Rules
- A story is posted only once it is **live** at `https://humasure.org/news/<slug>/`. Stories waiting for approval in WordPress are not public, so the approval gate also applies to Instagram.
- Stories are posted at most once each. `social/posted.json` records what has been posted.
- Newest stories go first, and stories older than 4 days are left to the website, so the feeds stay current and never flood.
- On Mondays the workflow checks that the token still works. If it fails, GitHub emails the repository owner.

## One-time setup (Jonathan; about 30 minutes)
The token below works like a key to the Instagram account. Enter it only in GitHub's secret settings. Never put it in chat, email or a file.

1. **Create the app.** At developers.facebook.com, go to My Apps → Create app and pick the Business type. Add Instagram using the "API setup with Facebook login" option.
2. **Get a user token.** Open Tools → Graph API Explorer and select the app. Under User Token, add these permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
   - `business_management`

   Click **Generate Access Token**. When asked, choose the Humasure Facebook Page and @humasureai.
3. **Turn it into a permanent Page token.**
   - In Tools → Access Token Debugger, paste the token and click **Extend Access Token**.
   - Back in Graph API Explorer, use the extended token to run `GET me/accounts`.
   - Copy the Humasure Page's `id` and its `access_token`. A Page token made from an extended token does not expire.
4. **Get the Instagram account ID.** In Graph API Explorer, using the Page token, run `GET <page-id>?fields=instagram_business_account` and copy the `id` inside.
5. **Check it works.** Run `GET <instagram-id>?fields=username`. It should return `humasureai`.
6. **Add the secrets to GitHub.** In this repository, go to Settings → Secrets and variables → Actions → New repository secret, and add:
   - `IG_USER_ID`: the Instagram ID from step 4
   - `IG_ACCESS_TOKEN`: the Page token from step 3
7. **Test it.**
   - Go to Actions → Instagram → Run workflow, keep "Dry run" ticked, and read the log.
   - Then run it again with "Dry run" unticked to post the first story.

Menu names in Meta's dashboard change from time to time. If a step looks different, the idea is the same: a permanent Page token with the five permissions above, plus the Instagram account ID.

## Facebook mirroring
Each run also posts every Instagram carousel to the Humasure Ai Facebook Page (ID `1504545736066506`) as a 3-photo post. On Facebook the caption carries a clickable link to the story instead of "link in bio". Stories already on Instagram are mirrored on the next run. `social/posted.json` records each `fb_post_id`.

One-time requirement: the Page token in `IG_ACCESS_TOKEN` must include `pages_manage_posts`.
1. In Graph API Explorer, add `pages_manage_posts` to the permission list. If it is not offered, first add it to the app's "Manage everything on your Page" use case.
2. Click Generate Access Token → Edit settings, keep the Humasure Ai Page and @humasureai selected, then extend the token.
3. Choose the Page under "User or Page", copy the Page token with the copy button, and replace the `IG_ACCESS_TOKEN` secret in GitHub.

If the permission is missing, Instagram posting carries on and the run log shows a "Facebook mirror failed" warning.
To stop mirroring, add the repository variable or secret `FB_MIRROR=0` and pass it to the workflow.
