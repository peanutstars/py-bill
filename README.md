# py-bill

Test Code


## Reference Sites

#### NGINX, uWSGI and Let's Encryption
+ https://www.raspberrypi-spy.co.uk/2018/12/running-flask-under-nginx-raspberry-pi/
+ https://webcodr.io/2018/02/nginx-reverse-proxy-on-raspberry-pi-with-lets-encrypt/


## Run with the debug mode

    DEBUG=1 uwsgi --ini uwsgi.debug.ini



## Setup for sending email with GMail

#### Store .credentials folder
+ Normally, find it in $USER/.credentials folder.
+ Raspberry pi, find it in /var/www/.credentials folder.

#### User configuration
It needs /var/pybill/config/config.yml file for the user configuration.

    user:
        url: https://your_domain_name/

    admin:
        email: your_email_address


## DB

#### Migration
It applied Flask-Migrate and Flask-Script after tag of v0.4. It need the follow process, if schema of database changed .

    #> sudo systemctl stop uwsgi-py-bill.service
    #> cd /opt/psapps/pybill
    #> sudo -u www-data python3 app.py db upgrade
    #> sudo systemctl start uwsgi-py-bill.service