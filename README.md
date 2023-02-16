# django_mail_sender
Service for sending email distribution using a templates and a subscribers lists

Service use celery and redis for async tasks. On main page there is instructions for using service in Russian language.

Default subscribers list includes only one variable - email, but user can add extra variables for using in the templates.
Subscribers list fills manuality. It could be improved by adding loading from file, csv for example. Or from google docs.

Templates can be loaded from html file or inserted/typed manuality. 
Template page contains WYSIWYG editor, which provides edititng html source and see what would be in the result.
There is feature of loading variables from subscribers list by chosing it in menu. 
When list is chosen user can print '{' and then will have appeared autocomplete menu. 
In subject field user can use variables too, but autocomplete will not have appeared.
If user typed variable tag with error then will showed error message in the form.
Images and additional files can not be loaded to service. As a result user needs to save this on his own server.
As improvement could be added downloading to service server.(and parsing links with downloading all files and replace links in final template.)

When subscribers list and template are ready the task can be created. For creating task needs chose a tamplate and subscribers list.
If the template contains variables which there are not in subscribers list will be showed warning message. 

There arent callbacks for any autoupdates on the client side yet. Apparently it will be made through websockets by Django Channels.
Service provides posibility for check messages for the reading, but not the delivery status. 
Checking status could be realised using local email server and analyse logs or schduled requests to imap server, with analyse email headers.

I have a lot of ideas, but i think i took too much time and there is non-zero posibility that my work will not have be honored. 
In any case i beg you to leave feedback. It very important for me. swetocopy@gmail.com
