# Project Setup Guide

## 1. Update the System (Optional)
```bash
sudo apt update
```

## 2. Clone the project and open the folder
```bash
git clone <repository-url>
cd <repository-folder>
```

## 3. Install Python 3.10 and pip:
```
sudo apt install python3.10
sudo apt install python3-pip
```

## 4. Install Requirements
```
pip install -r requirements.txt
```

## 5. Create the Database:
```
python3
from app import db
db.create_all()
```

## 6. Install perl (if not installed):
```
curl -L http://xrl.us/installperlnix | bash
```

## 7. install perl modules:
```bash
sudo apt-get install libgd-dev 
sudo apt-get install libgd-perl # for GD
```
Run CPAN to install additional modules:
```
cpan
install GD
install Math::Random 
install Term::ProgressBar
install GD::SVG
install Statistics::Basic
```

## 8. Create folders for generated files:
```
mkdir terrains
mkdir imgs
```

## 9. Install Gunicorn 3 and Nginx:
```
sudo apt install gunicorn3
sudo apt install nginx
```

## 10. Configure the Server:
Edit the Nginx configuration file:
```bash
sudo nano /etc/nginx/sites-enabled/flask_app
```
Add the following code:
```nano
server {
        listen 80;

        location / {
                proxy_pass http://127.0.0.1:8000;
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
}
```

## 11. Unlink default website on the server:
```
sudo unlink /etc/nginx/sites-enabled/default
```

## 12. Check if the Configuration is OK:
```
sudo nginx -t
```

## 13. Reload the Server:
```
sudo nginx -s reload
```

## 14. Open Port 8000:
```
sudo ufw allow 8000
```

## Optional: Change SECRET_KEY in config.py
```python
# In config.py
SECRET_KEY = 'your-new-secret-key'
```

## 15. Start the application:
Start the application with Gunicorn. Adjust the number of workers as needed:
```
gunicorn3 --workers=3 app:app
```
To run it 24/7, add the --daemon flag:
```
gunicorn3 --workers=3 --daemon app:app
```
