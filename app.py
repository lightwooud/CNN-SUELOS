from __future__ import division, print_function

from flask import Flask, request, session, redirect, url_for, render_template, flash
import psycopg2 #pip install psycopg2 
import psycopg2.extras
import re 
from werkzeug.security import generate_password_hash, check_password_hash
import urllib.request
from datetime import datetime
# Keras 
from keras.models import load_model
from keras.applications.imagenet_utils import preprocess_input
# Flask 
from werkzeug.utils import secure_filename
import os
import numpy as np
import cv2

width_shape = 190
height_shape = 190

names = ['SUELO DEGRADADO','SUELO FERTIL']

app = Flask(__name__)
app.secret_key = 'cairocoders-ednalan'

# Path del modelo preentrenado
MODEL_PATH = 'models/models_VGG19.h5'

DB_HOST = "localhost"
DB_NAME = "vision"
DB_USER = "postgres"
DB_PASS = "123456"

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

# Cargamos el modelo preentrenado
model = load_model(MODEL_PATH)

print('Modelo cargado exitosamente. Verificar http://127.0.0.1:5000/')

def model_predict(img_path, model):

    img=cv2.resize(cv2.imread(img_path), (width_shape, height_shape), interpolation = cv2.INTER_AREA)
    x=np.asarray(img)
    x=preprocess_input(x)
    x = np.expand_dims(x,axis=0)
    
    preds = model.predict(x)
    return preds




@app.route('/')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
   
        # User is loggedin show them the home page
        return render_template('index.html')
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
  
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        print(password)

        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        # Fetch one record and return result
        account = cursor.fetchone()

        if account:
            password_rs = account['password']
            print(password_rs)
            # If account exists in users table in out database
            if check_password_hash(password_rs, password):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                # Redirect to home page
                return redirect(url_for('home'))
            else:
                # Account doesnt exist or username/password incorrect
                flash('Incorrect username/password')
        else:
            # Account doesnt exist or username/password incorrect
            flash('Incorrect username/password')

    return render_template('login.html')
 
@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
   
        _hashed_password = generate_password_hash(password)

        #Check if account exists using MySQL
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        print(account)
        # If account exists show error and validation checks
        if account:
            flash('Account already exists!')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!')
        elif not username or not password or not email:
            flash('Please fill out the form!')
        else:
            # Account doesnt exists and the form data is valid, now insert new account into users table
            cursor.execute("INSERT INTO users (fullname, username, password, email) VALUES (%s,%s,%s,%s)", (fullname, username, _hashed_password, email))
            conn.commit()
            flash('You have successfully registered!')
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash('Please fill out the form!')
    # Show registration form with message (if any)
    return render_template('register.html')

  
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))
 
@app.route('/profile')
def profile(): 
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
  
    # Check if user is loggedin
    if 'loggedin' in session:
        cursor.execute('SELECT * FROM users WHERE id = %s', [session['id']])
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/update', methods=['POST'])
def update_user():
    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        email = request.form['email']
        
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            UPDATE users
            SET fullname = %s,
                username = %s,
                email = %s
            WHERE id = %s
        """, (fullname, username, email, id))            
        conn.commit()
        flash('usuario modificado correctamente')
        return redirect(url_for('profile'))
    

@app.route('/edit', methods = ['POST', 'GET'])
def get_user():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'loggedin' in session:
        cur.execute('SELECT * FROM users WHERE id = %s',[session['id']])
        account = cur.fetchone()
        return render_template('edit.html', users=account)
    return redirect(url_for('profile'))

@app.route('/predict', methods=['GET', 'POST'])
def upload():
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    now = datetime.now()
    print(now)
    if request.method == 'POST':

        # Obtiene el archivo del request
        f = request.files['file']

        # Graba el archivo en ./uploads
        
        file_path = os.path.join(
             'uploads', secure_filename(f.filename))
        f.save(file_path)
        cur.execute("INSERT INTO images (file_name, uploaded_on) VALUES (%s, %s)",[file_path, now])
        conn.commit
        
        
        # Predicción
        preds = model_predict(file_path, model)

        print('PREDICCIÓN', names[np.argmax(preds)])
        
        # Enviamos el resultado de la predicción
        result = str(names[np.argmax(preds)]) 
        cur.execute("INSERT INTO historial (id_images, resultado) VALUES (%s,%s)", [file_path,result])             
        conn.commit()
        return result

    return None



if __name__ == "__main__":
    app.run(debug=True)

