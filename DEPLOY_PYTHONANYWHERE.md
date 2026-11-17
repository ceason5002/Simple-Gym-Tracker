# Deploying to PythonAnywhere (free)

The site will live at `https://YOURNAME.pythonanywhere.com`. In every step below, replace
`YOURNAME` with your PythonAnywhere username.

SQLite works as-is here: PythonAnywhere keeps your files between reloads, so accounts and
lifts are not wiped the way they are on Render's free tier.

## 1. Create an account

Sign up at https://www.pythonanywhere.com and choose the free **Beginner** plan.
Your username becomes your site address.

## 2. Get the code and install it

Open **Consoles → Bash** and run:

```bash
git clone https://github.com/ceason5002/Simple-Gym-Tracker.git
cd Simple-Gym-Tracker
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `python3.13` is not found, use the newest one available (`python3.12`, `python3.11` or
`python3.10`; Django 5.2 needs 3.10 or newer). Remember which version you used for step 3.

Create the secrets file (it is git-ignored and never leaves the server):

```bash
echo "DJANGO_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')" > .env
echo "DJANGO_DEBUG=0" >> .env
```

Set up the database and static files:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## 3. Create the web app

1. Open the **Web** tab and click **Add a new web app**.
2. Click **Next**, choose **Manual configuration** (not "Django"), then pick the **same Python
   version** you used in step 2.
3. On the web app page, set:
   - **Source code:** `/home/YOURNAME/Simple-Gym-Tracker`
   - **Working directory:** `/home/YOURNAME/Simple-Gym-Tracker`
   - **Virtualenv:** `/home/YOURNAME/Simple-Gym-Tracker/.venv`
4. Click the **WSGI configuration file** link, delete everything in it, and paste:

   ```python
   import os
   import sys

   path = "/home/YOURNAME/Simple-Gym-Tracker"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

   Save it.
5. Under **Static files**, add one entry:
   - URL: `/static/`
   - Directory: `/home/YOURNAME/Simple-Gym-Tracker/staticfiles`
6. Under **Security**, turn on **Force HTTPS**.
7. Click the green **Reload** button at the top, then open `https://YOURNAME.pythonanywhere.com`.

If something goes wrong, the **Error log** link on the Web tab shows the Python traceback.

## Updating the site later

After pushing new commits to GitHub, open a Bash console and run:

```bash
cd ~/Simple-Gym-Tracker
source .venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then click **Reload** on the Web tab.

## Free-plan limits to know

- Free sites must be renewed: log in at least once a month and click **Run until 1 month from
  today** on the Web tab, or the site is switched off. They email a reminder a week before.
- Outbound internet access from free accounts is limited to an allowlist. This app does not
  call any outside services, so it is not affected.
- Disk space and CPU time are limited, which is plenty for this app.
