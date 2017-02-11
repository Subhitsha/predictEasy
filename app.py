import os
import time
from flask import Flask, render_template, json, request,redirect,session,url_for, send_from_directory,flash
from flaskext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash,secure_filename
import re
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from forms import SignupForm, LoginForm
import numpy as np
from sklearn.preprocessing import Imputer
from sklearn.cross_validation import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score


# stdlib
from json import dumps

def to_json(model):
    """ Returns a JSON representation of an SQLAlchemy-backed object.
    """
    json = {}
    json['fields'] = {}
    json['pk'] = getattr(model, 'id')

    for col in model._sa_class_manager.mapper.mapped_table.columns:
        json['fields'][col.name] = getattr(model, col.name)

    return dumps([json])


mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'why would I tell you my secret key?'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config.from_pyfile('app.cfg')
db = SQLAlchemy(app)

# MySQL configurations

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    password = db.Column(db.String(120))
    email = db.Column(db.String(240))

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.set_password(password)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return '<User %r>' % self.name


@app.before_request
def check_user_status():
    if 'user_email' not in session:
        session['user_email'] = None
        session['user_name'] = None





# MySQL configurations

class Comments(db.Model):
  # Setting the table name and
  # creating columns for various fields
  __tablename__ = 'comments' 
  id = db.Column('comment_id', db.Integer, primary_key=True)
  filename=db.Column(db.String(100))
  pub_date = db.Column(db.DateTime)

  def __init__(self,filename):
      # Initializes the fields with entered data
      # and sets the published date to the current time
      self.filename=filename
      self.pub_date = datetime.now()

# The default route for the app. 
# Displays the list of already entered comments
# We are getting all the comments ordered in 
# descending order of pub_date and passing to the
# template via 'comments' variable

@app.route('/show_all')
def show_all():
  return render_template('show_all.html', comments=Comments.query.order_by(Comments.pub_date.asc()).all()  )

@app.route('/show_all/<id>')
def get_data(id):
    quer=Comments.query.get(id)
    if not quer:
        return  'Does not exists'
    else:
        cancer_data = np.genfromtxt(fname='uploads/'+quer.filename, delimiter= ',', dtype= float)
        print "Dataset Lenght:: ", len(cancer_data)
        print "Dataset:: ", str(cancer_data)
        print "Dataset Shape:: ", cancer_data.shape
        cancer_data = np.delete(arr = cancer_data, obj= 0, axis = 1)
        X = cancer_data[:,range(0,9)]
        Y = cancer_data[:,9]
        imp = Imputer(missing_values="NaN", strategy='median', axis=0)
        X = imp.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(
         X, Y, test_size = 0.3, random_state = 100)
        y_train = y_train.ravel()
        y_test = y_test.ravel()
        r = {}
        for K in range(25):
            K_value = K+1
            neigh = KNeighborsClassifier(n_neighbors = K_value, weights='uniform', algorithm='auto')
            neigh.fit(X_train, y_train) 
            y_pred = neigh.predict(X_test)
            r[str(K)] = y_pred
            print "Accuracy is ", accuracy_score(y_test,y_pred)*100,"% for K-Value:",K_value

        return json.dumps(r)




# This view method responds to the URL /new for the methods GET and POST
@app.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        file = request.files['file']
        
            # Make the filename safe, remove unsupported chars
        filename = secure_filename(file.filename)
            # Move the file form the temporal folder to the uploadz
            # folder we setup
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Save the filename into a list, we'll use it later
        # The request is POST with some data, get POST data and validate it.
        # The form data is available in request.form dictionary.
        # Check if all the fields are entered. If not, raise an error
            # The data is valid. So create a new 'Comments' object
            # to save to the database
        comment = Comments(filename)
            # Add it to the SQLAlchemy session and commit it to
            # save it to the database
        db.session.add(comment)
        db.session.commit()
        # Flash a success message
        flash('File was successfully Uploaded')
            
            # Redirect to the view showing all the comments
        return redirect(url_for('show_all'))
    
    # Render the form template if the request is a GET request or
    # the form validation failed
    return render_template('new.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.route('/prepare')
def get_prepare():
    return render_template('prepare.html')


@app.route('/train')
def get_train():
    return render_template('train.html')

@app.route('/userHome')
def userHome():
    if session.get('user'):
        return render_template('layout.html')
    else:
        return render_template('error.html',error = 'Unauthorized Access')



@app.route('/', methods=('GET', 'POST'))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.check_password(form.password.data):
            session['user_email'] = form.email.data
            session['user_name'] = user.name
            return redirect(url_for('new'))
        else:
            flash('Sorry! no user exists with this email and password')
            return render_template('error.html')
    return render_template('login.html', form=form)


@app.route('/signup', methods=('GET', 'POST'))
def signup():
    if session['user_email']:
        flash('you are already signed up')
        return redirect(url_for('login'))
    form = SignupForm()
    if form.validate_on_submit():
        user_email = User.query.filter_by(email=form.email.data).first()
        if user_email is None:
            user = User(form.name.data, form.email.data, form.password.data)
            db.session.add(user)
            db.session.commit()
            session['user_email'] = form.email.data
            session['user_name'] = form.name.data
            return redirect(url_for('login'))
        else:
            return render_template('error1.html')
    return render_template('signup.html', form=form)


@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect(url_for('login'))


    

if __name__ == "__main__":
    db.create_all()
    app.run(port =5003,debug = True)
