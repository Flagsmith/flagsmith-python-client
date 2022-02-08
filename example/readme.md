# Flagsmith Basic Python Example

This directory contains a basic Flask application which utilises Flagsmith. To run the example application, you'll 
need to go through the following steps:

1. Create an account, organisation and project on [Flagsmith](https://flagsmith.com)
2. Create a feature in the project called "secret_button"
3. Give the feature a value using the json editor as follows: 

```json
{"colour": "#ababab"}
```

4. Create a .env file from the template located in this directory with the environment key of one of the environments 
in flagsmith (This can be found on the 'settings' page accessed from the menu on the left under the chosen environment.)
5. From a terminal window, export those environment variables (either manually or by using `export $(cat .env)`)
6. Run the app using `flask run`
7. Browse to http://localhost:5000

Now you can play around with the 'secret_button' feature in flagsmith, turn it on to show it and edit the colour in the
json value to edit the colour of the button. You can also identify as a given user and then update the settings for the
secret button feature for that user in the flagsmith interface to see the affect that has too. 
