from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from pymongo import MongoClient
import psycopg2
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Flask secret key
app.secret_key = os.getenv('SECRET_KEY')

# Connect to MongoDB
mongo_client = MongoClient(os.getenv('MONGO_URI'))
mongo_db = mongo_client[os.getenv('MONGO_DB_NAME')]
saved_articles_collection = mongo_db["SavedArticles"]

# Database connection function to PostgreSQL
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            database=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD')
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

# Function to initialize preferences in the database
def initialize_preferences():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Insert preferences if they don't exist
    preferences = [("1", "Technology"), ("2", "Sports"), ("3", "Business")]
    for pref_id, pref_name in preferences:
        cur.execute("SELECT preference_id FROM preferences WHERE preference_id = %s", (pref_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO preferences (preference_id, preference_name) VALUES (%s, %s)", (pref_id, pref_name))
    
    conn.commit()
    cur.close()
    conn.close()

# Call the function to initialize preferences
initialize_preferences()

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch preferences ordered by preference_id to maintain consistency
        cur.execute("SELECT * FROM preferences ORDER BY preference_id")
        preferences = cur.fetchall()

        cur.close()
        conn.close()

        # Render the signup form and pass the preferences to the template
        return render_template('signup.html', preferences=preferences)

    if request.is_json:  # Handle JSON request from Fetch API (for POST)
        data = request.get_json()
        username = data['username']
        password = data['password']
        preferences = data['preferences']

        # Define correct preference names
        preference_map = {
            "1": "Technology",
            "2": "Sports",
            "3": "Business"
        }

        if len(preferences) < 1 or len(preferences) > 3:
            return jsonify({'success': False, 'message': 'Please select at least 1 and at most 3 preferences.'})

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Database connection failed.'})

        cur = conn.cursor()

        try:
            # Insert the user into the Users table
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING user_id",
                (username, password)
            )
            user_id = cur.fetchone()[0]

            # Insert preferences into the Preferences table if they don't already exist
            for pref_id in preferences:
                pref_name = preference_map.get(pref_id)

                cur.execute("SELECT preference_id FROM preferences WHERE preference_name = %s", (pref_name,))
                pref_exists = cur.fetchone()

                if not pref_exists:
                    cur.execute(
                        "INSERT INTO preferences (preference_id, preference_name) VALUES (%s, %s)",
                        (pref_id, pref_name)
                    )

                # Insert the user-preference relationship into users_preferences
                cur.execute(
                    "INSERT INTO users_preferences (user_id, preference_id) VALUES (%s, %s)",
                    (user_id, pref_id)
                )

            conn.commit()

            return jsonify({'success': True})

        except psycopg2.IntegrityError as e:
            conn.rollback()
            # Handle duplicate username error
            if 'users_username_key' in str(e):
                return jsonify({'success': False, 'message': 'Username already exists. Please choose a different one.'})
            else:
                return jsonify({'success': False, 'message': 'An error occurred during signup. Please try again.'})

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

        finally:
            cur.close()
            conn.close()

    return jsonify({'success': False, 'message': 'Invalid request format. Please use JSON.'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    if request.is_json:  # Handle JSON request from Fetch API
        data = request.get_json()
        username = data['username']
        password = data['password']

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Database connection failed.'})

        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password.'})

    return jsonify({'success': False, 'message': 'Invalid request format. Please use JSON.'})

@app.route('/change_preferences', methods=['GET', 'POST'])
def change_preferences():
    if request.method == 'GET':
        user_id = session.get('user_id')

        if not user_id:
            flash('Please log in first.')
            return redirect(url_for('login'))

        conn = get_db_connection()
        cur = conn.cursor()

        # Get all available preferences in a consistent order (by preference_id)
        cur.execute("SELECT * FROM preferences ORDER BY preference_id")
        all_preferences = cur.fetchall()

        # Get the user's current preferences
        cur.execute("""
            SELECT p.preference_id 
            FROM users_preferences up 
            JOIN Preferences p ON up.preference_id = p.preference_id 
            WHERE up.user_id = %s
        """, (user_id,))
        current_preferences = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

        return render_template('changePreferences.html', 
                               all_preferences=all_preferences, 
                               current_preferences=current_preferences)

    if request.method == 'POST':
        data = request.get_json()
        user_id = session.get('user_id')
        preferences = data['preferences']

        if not user_id:
            return jsonify({'success': False, 'message': 'User not logged in.'})

        if len(preferences) < 1 or len(preferences) > 3:
            return jsonify({'success': False, 'message': 'Select at least 1 and at most 3 preferences.'})

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Remove the user's existing preferences
            cur.execute("DELETE FROM users_preferences WHERE user_id = %s", (user_id,))

            # Insert the new preferences
            for pref_id in preferences:
                cur.execute("INSERT INTO users_preferences (user_id, preference_id) VALUES (%s, %s)", (user_id, pref_id))

            conn.commit()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
        finally:
            cur.close()
            conn.close()

    return jsonify({'success': False, 'message': 'Invalid request format.'})

# Route to get user preferences based on the logged-in user
@app.route('/get_user_preferences')
def get_user_preferences():
    if 'user_id' in session:
        user_id = session['user_id']
        conn = get_db_connection()  # Get a new connection
        cur = conn.cursor()
        cur.execute("""
            SELECT preference_name 
            FROM preferences p
            JOIN users_preferences up ON p.preference_id = up.preference_id
            WHERE up.user_id = %s
        """, (user_id,))
        preferences = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()  # Close the connection
        return jsonify(preferences)
    return jsonify([]), 401

# Route to fetch articles based on user preferences
@app.route('/fetch_articles')
def fetch_articles():
    if 'user_id' not in session:
        return jsonify([]), 401  # User not logged in

    try:
        user_id = session['user_id']

        # Fetch user's preferences
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT preference_name 
            FROM preferences p
            JOIN users_preferences up ON p.preference_id = up.preference_id
            WHERE up.user_id = %s
        """, (user_id,))
        preferences = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()

        # Prepare a list to hold all articles to display
        articles_to_display = []
        GUARDIAN_API_KEY = os.getenv('GUARDIAN_API_KEY')

        for pref in preferences:
            # Query cached articles for the current preference
            cached_articles = list(mongo_db.CachedArticles.find(
                {"user_id": user_id, "search_term": pref}
            ).limit(10))

            # Flag cached articles for display
            for article in cached_articles:
                article['is_cached'] = True

            # Add cached articles to display list
            articles_to_display.extend(cached_articles)

            # Check if more articles are needed from the API
            if len(cached_articles) < 10:
                response = requests.get(
                    "https://content.guardianapis.com/search",
                    params={"q": pref, "api-key": GUARDIAN_API_KEY}
                )
                if response.status_code == 200:
                    fetched_articles = response.json().get('response', {}).get('results', [])
                    
                    # Cache and flag new articles
                    for article in fetched_articles[:10 - len(cached_articles)]:
                        article["cached_at"] = datetime.utcnow()
                        article["user_id"] = user_id
                        article["search_term"] = pref  # Use preference as search term
                        mongo_db.CachedArticles.insert_one(article)  # Cache new article
                        article['is_cached'] = False  # Not from cache

                    # Add API-fetched articles to display list
                    articles_to_display.extend(fetched_articles[:10 - len(cached_articles)])

        # Convert articles to JSON-compatible format and exclude '_id'
        articles_to_display = [
            {k: v for k, v in article.items() if k != "_id"}
            for article in articles_to_display
        ]

        return jsonify(articles_to_display)

    except Exception as e:
        print(f"Error in fetch_articles: {e}")
        return jsonify({'error': 'An error occurred while fetching articles.'}), 500

@app.route('/save_article', methods=['POST'])
def save_article():
    if 'user_id' in session:
        article_data = request.get_json()
        article_data['user_id'] = session['user_id']  # Track user saving the article
        article_data['saved_at'] = datetime.utcnow()   # Add saved_at timestamp
        
        # Check if the article is already saved for this user to avoid duplicates
        if not saved_articles_collection.find_one({"webUrl": article_data["webUrl"], "user_id": article_data["user_id"]}):
            saved_articles_collection.insert_one(article_data)
            return jsonify({'success': True, 'message': 'Article saved successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Article already saved.'})
    return jsonify({'success': False, 'message': 'User not logged in.'})

@app.route('/get_saved_articles')
def get_saved_articles():
    if 'user_id' in session:
        user_id = session['user_id']
        # Find saved articles for the logged-in user only
        saved_articles = list(saved_articles_collection.find({"user_id": user_id}, {"_id": 0, "user_id": 0}))
        return jsonify(saved_articles)
    return jsonify([]), 401

@app.route('/delete_article', methods=['POST'])
def delete_article():
    if 'user_id' in session:
        data = request.get_json()
        url = data.get('url')
        user_id = session['user_id']

        # Remove the article with the specified URL for the logged-in user
        result = saved_articles_collection.delete_one({"webUrl": url, "user_id": user_id})

        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Article deleted successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Article not found or not deleted.'})
    return jsonify({'success': False, 'message': 'User not logged in.'}), 401

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return render_template('dashboard.html', user_id=session['user_id'])
    else:
        flash('Please log in first.')
        return redirect(url_for('login'))

@app.route('/news_feed')
def news_feed():
    return render_template('newsFeed.html')

@app.route('/saved_articles')
def saved_articles():
    return render_template('savedArticles.html')

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/main')
def main():
    return render_template('main.html')

@app.route('/logout')
def logout():
    # Clear the session data
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)