
![ezEngine Screenshot](https://s8.uupload.ir/files/exo_34ww.jpg)

# Version

## V 2.0

<hr>

## How Do i Put My Bot Token in the Source 

<hr>
 

## Follow The Instructions

1. create .env file inside the same folder `open with editor file`

2. And put it in the bot token file like this `BOT_TOKEN=YOUR_TOKEN_BOT`

3. Run This command `export BOT_TOKEN=YOUR_TOEKN_BOT`

4. And this Command `echo $BOT_TOKEN`


If You Execute This Command `echo $BOT_TOKEN` And Your Bot Token Is Not Displayed in The CLI environment You Will Get An Error To Aviod Getting The Error Do All The Things I Said 

## Database 

Open Sp.py and change database 

````
DB_NAME = os.getenv('DB_NAME', 'Database_Name')
DB_HOST = os.getenv('DB_HOST', 'Database_Host')
DB_USER = os.getenv('DB_USER', 'Database_Username')
DB_PASS = os.getenv('DB_PASS', 'Database_Password')
````
<h4>For Create User For Bomber Bot </h4>

Run Command `mysql` your server

````
Create database ExoBot;
create user 'Exo'@'localhost' identified with mysql_native_password by 'Favorite password';
grant all on ExoBot.* to 'z0roday'@'localhost';
````

Your DataBase Created `Where i Wrote change Exo and put your favorite thinds `

````
cd Exo-Sms-Bomber-Bot-Backup


<a src="hhtps://t.me/z0roday">
pip -r install requriments.txt
python Sp.py 
````
And Run Your Bot 



