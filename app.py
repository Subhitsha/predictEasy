import os
import time
import random
from flask import Flask, render_template, json, request,redirect,session,url_for, send_from_directory,flash
from flaskext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash,secure_filename
import re
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from forms import SignupForm, LoginForm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn import preprocessing
from sklearn.preprocessing import Imputer
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.feature_selection import SelectFromModel, VarianceThreshold, SelectKBest, chi2
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn import tree
from sklearn.preprocessing import LabelEncoder
from sklearn.externals import joblib
import matplotlib.pyplot as plt






mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'why would I tell you my secret key?'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['DOWNLOAD_FOLDER'] = 'processed/'
app.config['ALLOWED_EXTENSIONS'] = set(['csv'])
app.config.from_pyfile('app.cfg')
db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

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
  id = db.Column('comment_id', db.Integer,primary_key=True)
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

@app.route('/show_all/')
def show_all():
  return render_template('show_all.html', comments=Comments.query.order_by(Comments.id.asc()).all()  )


@app.route('/show_all/<id>')
def get_data(id):
    quer = Comments.query.get(id)
    if not quer:
        return  'Does not exists'
    else:
        # read the csv into dataframe
        df = pd.read_csv('uploads/'+quer.filename)

        columns = df.columns
        return render_template('Prepare.html', data=quer, df=df, columns=columns)
       

@app.route('/prepare/<id>', methods=['GET', 'POST'])
def get_prepare(id):

    if request.method == 'POST':

        model_name = request.form['model']

        form_inputs = list(request.form.values())

        form_inputs.remove(model_name)



        clf = joblib.load('brain/'+ model_name +'.pkl') 

        features = preprocessing.scale([float(i) for i in form_inputs])
        a = clf.predict(features)
        return render_template('result.html', data=str(a[0]))
   

    if request.method == 'GET':
        filename = request.args.get('filename')
        features = request.args.getlist('features')
        target = request.args.get('target')
        missing = request.args.get('missing')
        algo = request.args.get('algo')
        feature_algo = request.args.get('feature_selection')
        top_feature_count = int(request.args.get('top_feature_count'))

        # read the dataset and convert to dataframe
        data = pd.read_csv('uploads/'+filename)

        # return data.to_html()


        # Select the target variable column name 'class'
        Y = data.pop(target)

        # Assign the features as X
        X = data[features]

        
        # Convert categorical columns into labels
        le = LabelEncoder()

        for col in X.columns.values:
            # Encode only categorical variable
            if X[col].dtypes == 'object':
                # Using whole data to form an exhaustive list of levels
                le.fit(X[col].values)
                X[col]=le.transform(X[col])


        # Replace all missing values in features with median of respective column
        imp = Imputer(missing_values="NaN", strategy=missing, axis=0)
        X = imp.fit_transform(X)


        # Discretization processing on X
        X = preprocessing.scale(X)


        # Save preprocessed dataset
        df = pd.DataFrame(X, index=[i for i in range(len(X))], columns=features)
        df.to_csv('processed/'+filename.split('.')[0]+'.csv', index=False)


        # To find best feature based on its importance
        feature_clf = ExtraTreesClassifier(n_estimators=250, random_state=0)
        feature_clf.fit(X, Y)

        feature_dict = {}
        for feature in zip(features, feature_clf.feature_importances_):
            feature_dict[feature[0]] = feature[1]*100


        # Create a selector object that will use the random forest classifier to identify
        # features that have an importance of more than 0.15
        if feature_algo == 'select_from_model':
            sfm = SelectFromModel(feature_clf, threshold=0.15)

        elif feature_algo == 'remove_low_variance':
            sfm = VarianceThreshold(threshold=(.8 * (1 - .8))) 

        # Train the selector
        sfm.fit(X, Y)


        # Print the names of the most important features
        most_important_features = [features[feature_list_index] for feature_list_index in sfm.get_support(indices=True)]
        best_features_df = pd.DataFrame(feature_dict.items(), columns=['Features', 'Score']).sort_values('Score', ascending=False)



        X = data[list(best_features_df.head(top_feature_count)['Features'])]


        # Replace all missing values in features with median of respective column
        imp = Imputer(missing_values="NaN", strategy=missing, axis=0)
        X = imp.fit_transform(X)

        # Discretization processing on X
        X = preprocessing.scale(X)



        # Split the dataset into 70% training and 30% testing set
        X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size = 0.3, random_state = 100)


        if algo == 'decision_tree':
            # initializees the Decision Tree algorithm
            clf = DecisionTreeClassifier()

        elif algo == 'knn':
            # Initializes the KNN classifier with 20 neighbors
            clf = KNeighborsClassifier(n_neighbors = 20, weights='uniform', algorithm='auto')

        elif algo == 'rfc':
            # initializees the RandomForest Decision Tree algorithm
            clf = RandomForestClassifier(n_estimators=100, max_depth=None, min_samples_split=2, random_state=0)


        # Train the instantiated model with 70% training data
        clf.fit(X_train, y_train) 
        # tree.export_graphviz(clf, out_file='tree.dot')

        # Save the trained model
        joblib.dump(clf,  'brain/'+ filename.split('.')[0] +'.pkl') 


        # Now model is ready and test using remaining 30%
        y_pred = clf.predict(X_test)

        # print 'Mean Square Error : {}'.format(mean_squared_error(y_test, y_pred)**0.5)
        # print 'Mean Absolute Error : {}'.format(mean_absolute_error(y_test, y_pred)**0.5)
        # print y_test
        # print y_pred

        # Result is been sent with accuracy, dataset, algorithm used, imputed method
        response =  {
            'accuracy' : accuracy_score(y_test,y_pred)*100,
            'dataset': filename,
            'algorithm': algo,
            'feature_selection': feature_algo,
            'imputer': missing,
            'target': target,
            'features': features,
            'output': best_features_df.to_html(classes="table table-condensed"),
            'id': id,
            'random': random,
            'best_features': best_features_df.head(top_feature_count)

        }

        return render_template('report.html', result=response)




@app.route('/<id>')
def get_file(id):
    que = Comments.query.get(id)
    db.session.delete(que)
    db.session.commit()
    response="deleted"
    return json.dumps(response)   


# This view method responds to the URL /new for the methods GET and POST
@app.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
        
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




@app.route('/processed/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    return send_from_directory(directory='processed', filename=filename)


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
