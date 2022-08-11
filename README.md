# Circle-CI dashboard for Redis projects

## Structure

* Project is running on heroku: https://circle-ci-dashboard.herokuapp.com/
* Run is through gunicorn. Start file is `Procfile`
* For running requires env variables:
    * DATABASE_URL - format is `postgresql://$username:$password@$host:$port/$db`
    * CIRCLE_CI_TOKEN
    * GITHUB_TOKEN - format is `token $token`

## Helpful commands

* get full logs: `heroku logs -a circle-ci-dashboard` 
* get web app logs: `heroku logs -a circle-ci-dashboard --dyno=web`
* get scheduler logs: `heroku logs --ps scheduler -a circle-ci-dashboard`