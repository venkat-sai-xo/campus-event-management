import os
import csv
import io
from flask import (Flask, render_template, redirect, url_for, flash,
                   request, abort, Response)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (UserMixin, LoginManager, login_user,
                         logout_user, login_required, current_user)
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, CSRFError
from wtforms import (StringField, PasswordField, SubmitField, TextAreaField,
                     SelectField, DateField, TimeField, IntegerField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                ValidationError, NumberRange)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, func
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'mysql+pymysql://root:password@localhost:3306/campus_db'
)

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

CATEGORIES = ['Technical', 'Cultural', 'Sports', 'Workshop']


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


# ---------- MODELS ----------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    roll_no = db.Column(db.String(30))
    department = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)

    registrations = db.relationship('Registration', backref='student',
                                    cascade='all, delete-orphan')


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    venue = db.Column(db.String(200), nullable=False)
    capacity = db.Column(db.Integer, default=50)
    poster = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    registrations = db.relationship('Registration', backref='event',
                                    cascade='all, delete-orphan')

    def seats_left(self):
        return self.capacity - len(self.registrations)


class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    attended = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'event_id'),)


# ---------- FORMS ----------

class SignupForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    roll_no = StringField('Roll Number', validators=[DataRequired()])
    department = StringField('Department', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm Password',
                            validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('This email is already registered.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class EventForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[(c, c) for c in CATEGORIES])
    date = DateField('Date', validators=[DataRequired()])
    time = TimeField('Time', validators=[DataRequired()])
    venue = StringField('Venue', validators=[DataRequired(), Length(max=200)])
    capacity = IntegerField('Capacity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Save Event')


# ---------- ERROR PAGES ----------

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403,
                           message="You don't have permission to open this page."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404,
                           message='The page you are looking for does not exist.'), 404


@app.errorhandler(CSRFError)
def csrf_error(e):
    return render_template('error.html', code=400,
                           message='Your session expired. Please go back, refresh the page and try again.'), 400


# ---------- PUBLIC / STUDENT ROUTES ----------

@app.route('/')
def home():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    when = request.args.get('when', '')

    query = Event.query

    if q:
        like = f'%{q}%'
        query = query.filter(or_(Event.title.ilike(like),
                                 Event.venue.ilike(like)))
    if category in CATEGORIES:
        query = query.filter(Event.category == category)

    today = datetime.now().date()
    if when == 'upcoming':
        query = query.filter(Event.date >= today)
    elif when == 'past':
        query = query.filter(Event.date < today)

    events = query.order_by(Event.date, Event.time).all()
    return render_template('index.html', events=events, categories=CATEGORIES,
                           q=q, category=category, when=when)


@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = db.get_or_404(Event, event_id)
    is_registered = False
    if current_user.is_authenticated and not current_user.is_admin:
        is_registered = Registration.query.filter_by(
            user_id=current_user.id, event_id=event.id).first() is not None
    is_past = event.date < datetime.now().date()
    return render_template('event_detail.html', event=event,
                           is_registered=is_registered, is_past=is_past)


@app.route('/event/<int:event_id>/register', methods=['POST'])
@login_required
def register_event(event_id):
    if current_user.is_admin:
        abort(403)
    event = db.get_or_404(Event, event_id)

    if event.date < datetime.now().date():
        flash('This event is already over.', 'warning')
    elif Registration.query.filter_by(user_id=current_user.id,
                                      event_id=event.id).first():
        flash('You are already registered for this event.', 'info')
    elif event.seats_left() <= 0:
        flash('Sorry, this event is full.', 'danger')
    else:
        db.session.add(Registration(user_id=current_user.id, event_id=event.id))
        db.session.commit()
        flash('You have registered successfully!', 'success')
    return redirect(url_for('event_detail', event_id=event.id))


@app.route('/event/<int:event_id>/cancel', methods=['POST'])
@login_required
def cancel_registration(event_id):
    if current_user.is_admin:
        abort(403)
    reg = Registration.query.filter_by(user_id=current_user.id,
                                       event_id=event_id).first()
    if reg:
        db.session.delete(reg)
        db.session.commit()
        flash('Your registration has been cancelled.', 'info')
    else:
        flash('You are not registered for this event.', 'warning')
    next_page = request.form.get('next')
    if next_page == 'my_events':
        return redirect(url_for('my_registrations'))
    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/my-events')
@login_required
def my_registrations():
    if current_user.is_admin:
        abort(403)
    regs = (Registration.query
            .filter_by(user_id=current_user.id)
            .join(Event)
            .order_by(Event.date, Event.time)
            .all())
    return render_template('my_registrations.html', regs=regs)


# ---------- ADMIN ROUTES ----------

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    today = datetime.now().date()
    stats = {
        'events': Event.query.count(),
        'upcoming': Event.query.filter(Event.date >= today).count(),
        'students': User.query.filter_by(is_admin=False).count(),
        'registrations': Registration.query.count(),
    }
    top_events = (db.session.query(Event, func.count(Registration.id))
                  .outerjoin(Registration, Registration.event_id == Event.id)
                  .group_by(Event.id)
                  .order_by(func.count(Registration.id).desc())
                  .limit(5).all())
    recent = (Registration.query
              .order_by(Registration.registered_at.desc())
              .limit(5).all())
    return render_template('admin_dashboard.html', stats=stats,
                           top_events=top_events, recent=recent)


@app.route('/admin/event/new', methods=['GET', 'POST'])
@admin_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(title=form.title.data,
                      description=form.description.data,
                      category=form.category.data,
                      date=form.date.data,
                      time=form.time.data,
                      venue=form.venue.data,
                      capacity=form.capacity.data)
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('event_detail', event_id=event.id))
    return render_template('event_form.html', form=form, heading='Create New Event')


@app.route('/admin/event/<int:event_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_event(event_id):
    event = db.get_or_404(Event, event_id)
    form = EventForm(obj=event)
    if form.validate_on_submit():
        event.title = form.title.data
        event.description = form.description.data
        event.category = form.category.data
        event.date = form.date.data
        event.time = form.time.data
        event.venue = form.venue.data
        event.capacity = form.capacity.data
        db.session.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('event_detail', event_id=event.id))
    return render_template('event_form.html', form=form, heading='Edit Event')


@app.route('/admin/event/<int:event_id>/delete', methods=['POST'])
@admin_required
def delete_event(event_id):
    event = db.get_or_404(Event, event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted.', 'info')
    return redirect(url_for('home'))


@app.route('/admin/event/<int:event_id>/registrations')
@admin_required
def event_registrations(event_id):
    event = db.get_or_404(Event, event_id)
    regs = (Registration.query
            .filter_by(event_id=event.id)
            .join(User, Registration.user_id == User.id)
            .order_by(User.name)
            .all())
    return render_template('event_registrations.html', event=event, regs=regs)


@app.route('/admin/event/<int:event_id>/registrations/csv')
@admin_required
def download_registrations(event_id):
    event = db.get_or_404(Event, event_id)
    regs = (Registration.query
            .filter_by(event_id=event.id)
            .join(User, Registration.user_id == User.id)
            .order_by(User.name)
            .all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['S.No', 'Name', 'Roll Number', 'Department', 'Email',
                     'Registered On', 'Attendance'])
    for i, r in enumerate(regs, start=1):
        writer.writerow([i, r.student.name, r.student.roll_no,
                         r.student.department, r.student.email,
                         r.registered_at.strftime('%d-%m-%Y %H:%M'),
                         'Present' if r.attended else 'Absent'])

    filename = f'registrations_event_{event.id}.csv'
    return Response('\ufeff' + output.getvalue(),
                    mimetype='text/csv',
                    headers={'Content-Disposition':
                             f'attachment; filename={filename}'})


@app.route('/admin/registration/<int:reg_id>/attendance', methods=['POST'])
@admin_required
def toggle_attendance(reg_id):
    reg = db.get_or_404(Registration, reg_id)
    reg.attended = not reg.attended
    db.session.commit()
    return redirect(url_for('event_registrations', event_id=reg.event_id))


# ---------- AUTH ROUTES ----------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = SignupForm()
    if form.validate_on_submit():
        user = User(name=form.name.data,
                    email=form.email.data.lower(),
                    roll_no=form.roll_no.data,
                    department=form.department.data,
                    password_hash=generate_password_hash(form.password.data),
                    is_admin=False)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash(f'Welcome, {user.name}!', 'success')
            next_page = request.args.get('next', '')
            # only allow redirects inside this site
            if not next_page.startswith('/') or next_page.startswith('//'):
                next_page = None
            if not next_page and user.is_admin:
                next_page = url_for('admin_dashboard')
            return redirect(next_page or url_for('home'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


# ---------- SETUP ----------

def setup_database():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(is_admin=True).first():
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin = User(name='Admin',
                         email='admin@college.com',
                         password_hash=generate_password_hash(admin_password),
                         is_admin=True)
            db.session.add(admin)
            db.session.commit()
            print('Admin created: admin@college.com')


if __name__ == '__main__':
    setup_database()
    app.run(debug=True)