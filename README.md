# Google Analytics superProxy

The Google Analytics superProxy allows you to publicly share your Google
Analytics reporting data. Use it to power your own custom dashboards and
widgets, transform responses to various formats, manage your quota
efficiently, test, and more. It handles authentication, caching, and
response-formatting for you.

The Google Analytics superProxy is a web application that runs in the
[Google App Engine](https://appengine.google.com/) python environment.

## Feature Highlights
- Publicly share your Google Analytics data
- Use the proxy to power your own custom dashboards
- Convert to CSV, Data Table, TSV
- Relative dates are supported (e.g. last 7 days)
- Automatically refreshes report data
- Caching - fast responses and efficient quota usage

## Setting up a local development environment
1.  If necessary, download and install [Python 2.7](http://www.python.org/getit/releases/2.7/)
2.  Download and install the [App Engine SDK for Python](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python)
3.  Create an [APIs Console Project](https://code.google.com/apis/console/).
  - Go to the [Services pane](https://code.google.com/apis/console/#:services)
    to activate the Analytics API service.
	- Go to the [API Access pane](https://code.google.com/apis/console/#:access)
    and create an OAuth 2.0 Client. For **Client ID** settings select
    **Web Application**. For the hostname click **more options** and then add
    the following to the **Authorized Redirect URIs** field:
    `http://localhost:8080/admin/auth`. **Note:** you may use a different port,
    but you need to use that port consistently throughout your project. Click on
    **Create client ID**.
4.  Edit `config.py` in the Google Analytics superProxy `src` directory. Update
    `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, and `OAUTH_REDIRECT_URI` with
	  the corresponding values from the OAuth 2.0 Client you created in the
    previous step. The redirect URI does not need to include `/admin/auth`,
    this will be added for you.
5.  (Optional): The default the timezone for resolving relative dates is the
    Pacific timezone. The default setting for "anonymizing" Core Reporting API
    responses is set to `False`. Both of these options can be configured in
    `src/controllers/util/co.py`.
6.  Add the Google Analytics superProxy app to the Google App Engine Launcher
    (File->Add Existing Application) or start the app using `dev_appserver.py`.
    For additional details see [The Development Environment](https://developers.google.com/appengine/docs/python/gettingstartedpython27/devenvironment).
    Make sure to serve the application using the same port as set in the list of
    **Authorized Redirect URIs** for your APIs Console Project, and in
    `config.py`.
7.  View the app by visiting [http://localhost:8080/admin](http://localhost:8080/admin)
    (replace `8080` with the correct port number).

## Hosting the application on App Engine
1.  Setup the local development environment as described above.
2.  Register an application ID for your application using the
    [App Engine Administration Console](https://appengine.google.com/). This
    will give you a free hostname on `appspot.com`.
3.  Edit the `app.yaml` file in the `src` directory of the Google Analytics
    superProxy and set the first line to the application ID you registered in
    the previous step. E.g. `application: your-application-id`.
4.  Edit or create a new
    [APIs Console Project](https://code.google.com/apis/console/#:access) and
    add the full URL of your application + `/admin/auth` as an
    **Authorized Redirect URI** for the OAuth 2.0 Client. If using the free
    appspot.com domain, the redirect URI will look something like
    `https://your-applciation-id.appspot.com/admin/auth`.
5.  Edit `config.py` in the Google Analytics superProxy `src` directory and
    update `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, and `OAUTH_REDIRECT_URI`
    if necessary.
6.  Using the Google App Engine Launcher or `appcfg.py` deploy the application.
    For details see
    [Uploading Your Application](https://developers.google.com/appengine/docs/python/gettingstartedpython27/uploading).
7.  View the app by visiting the `/admin` page of your application. E.g.
    [https://your-application-id.appspot.com/admin](https://your-application-id.appspot.com/admin).

### Creating your first public query
1.  See instructions above to get up and running, either with a local dev
    environment or on App Engine.
2.  View the application by visiting the `/admin` page. E.g.
    [https://your-application-id.appspot.com/admin](https://your-application-id.appspot.com/admin).
2. 	Follow the instructions to authenticate and authorize the application to
    access your Google Analytics account.
3.  Create a new query (a Core Reporting API query URI) and specify:
    - A name for the query (e.g. Top 10 Browsers for last 7 days)
    - Refresh interval - how often to update the report, in seconds (e.g. 3600
      to refresh this once an hour.)
    - The Query URI (e.g. [https://www.googleapis.com/analytics/v3/data/ga?ids=ga:XXXX&dimensions=ga:browser;metrics=ga:visits;sort=-ga:visits&max-results=10&start-date={6daysago}&end-date={today}]())
    - Tip: Use the
      [Google Analytics Query Explorer](http://ga-dev-tools.appspot.com/explorer/)
      to get a valid Query URI.
4.  Click **Save & Schedule Query** to save the query and start scheduling the
    query for automatic refresh. A new Public Request Endpoint (URL) will be
    created for this report.

Requests to the public endpoint URL will return the API response for the
specific report created. Authorization will not be required to access the
report data and it will automatically refresh.

### Additional Resources
- [Google Analytics superProxy](https://developers.google.com/analytics/solutions/google-analytics-super-proxy)
  (Google Analytics Developers)
  - [Managing Users](https://developers.google.com/analytics/solutions/google-analytics-super-proxy#manage-users)
  - [Domain Restrictions](https://developers.google.com/analytics/solutions/google-analytics-super-proxy#domain)
  - [Quota Considerations](https://developers.google.com/analytics/solutions/google-analytics-super-proxy#quota)

### Features
- OAuth 2.0 for authentication and it's all handled for you server side
-	Multiple users - each with their own set of queries
-	Automatic scheduling to refresh data at a configurable time interval
-	Caching of responses (saves on quota and it's fast)
- API Query stats (last request time and number public requests)
- Transform responses to CSV, Data Table, or TSV.
- Relative dates are supported for reporting queries (e.g. last 7 days).
- Timezone for relative dates can be configured (North American timezones and UTC).
- Auto-scheduling. Scheduling for an "abandoned" API query (i.e. hasn't been
  publicly requested for a long time) will be automatically paused, resuming
  only if is subsequently requested.
- Responses can "anonymized". If enabled, then Google Analytics profile IDs and
  other account information is removed from the public response.
- Error logging. Errors for scheduled API queries are logged. After an API Query
  (default) has 10 error responses, scheduling for the query is paused.
  - The Google Analytics superProxy will not publicly return error responses.
    Instead the last successful response will be returned.
- Public endpoints can be enabled/disabled if you want to stop sharing.
- Queries can be be refreshed on an adhoc basis instead of waiting for the next
  scheduled refresh.
- JSONP (add a `callback` parameter to the Public Endpoint request URL).

### Changelog
#### 2013-07-19
- Initial launch...super sweet!
