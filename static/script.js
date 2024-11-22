// Function to handle the signup form using Fetch API
function submitSignupForm(event) {
    event.preventDefault();  // Prevent the default form submission

    // Get the form values
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const preferences = Array.from(document.querySelectorAll('input[name="preferences"]:checked'))
        .map(pref => pref.value);  // Get selected preferences

    // Validate the number of preferences selected
    if (preferences.length < 1 || preferences.length > 3) {
        alert('Please select at least 1 and at most 3 preferences.');
        return false;
    }

    // Prepare data to send to the server
    const formData = {
        username: username,
        password: password,
        preferences: preferences
    };

    // Send the form data to the server using Fetch API
    fetch('/signup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Signup successful! You can now log in.');
            window.location.href = '/login';  // Redirect to login page
        } else {
            alert('Error during signup: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error during form submission:', error);
        alert('An error occurred. Please try again.');
    });
}

// Function to handle the login form using Fetch API
function submitLoginForm(event) {
    event.preventDefault();  // Prevent the default form submission

    // Get the form values
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    // Prepare data to send to the server
    const formData = {
        username: username,
        password: password
    };

    // Send the form data to the server using Fetch API
    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/dashboard';  // Redirect to dashboard page
        } else {
            alert('Invalid username or password.');
        }
    })
    .catch(error => {
        console.error('Error during form submission:', error);
        alert('An error occurred. Please try again.');
    });
}

// Attach the functions to the form's submit events
document.addEventListener('DOMContentLoaded', function () {
    const signupForm = document.querySelector('form#signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', submitSignupForm);
    }

    const loginForm = document.querySelector('form#login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', submitLoginForm);
    }
});

function submitPreferencesForm(event) {
    event.preventDefault();

    const preferences = Array.from(document.querySelectorAll('input[name="preferences"]:checked'))
        .map(pref => pref.value);

    if (preferences.length < 1 || preferences.length > 3) {
        alert('Please select at least 1 and at most 3 preferences.');
        return;
    }

    const formData = { preferences: preferences };

    fetch('/change_preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        // Show a simple alert with the server response message
        if (data.success) {
            alert(data.message || 'Preferences updated successfully!');
        } else {
            alert(data.message || 'Error updating preferences. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
    });
}

// Attach the function to the form's submit event
document.addEventListener('DOMContentLoaded', function () {
    const preferencesForm = document.getElementById('preferences-form');
    if (preferencesForm) {
        preferencesForm.addEventListener('submit', submitPreferencesForm);
    }
});

document.addEventListener('DOMContentLoaded', function () {
    // Fetch and display user preferences
    fetch('/get_user_preferences')
        .then(response => response.json())
        .then(preferences => {
            const prefsList = document.getElementById('user-preferences');
            preferences.forEach(pref => {
                const li = document.createElement('li');
                li.textContent = pref;
                prefsList.appendChild(li);
            });
        });

    // Fetch and display articles based on user preferences
    document.getElementById('fetch-articles').addEventListener('click', function () {
        fetch('/fetch_articles')
            .then(response => response.json())
            .then(articles => {
                const articlesDiv = document.getElementById('articles');
                articlesDiv.innerHTML = '';  // Clear previous articles

                articles.forEach(article => {
                    const articleDiv = document.createElement('div');
                    articleDiv.classList.add('article-box'); // Apply styling class

                    // Determine label for each article
                    const labelClass = article.is_cached ? 'cached-label' : 'api-label';
                    const labelText = article.is_cached ? 'Cached Article' : 'API Fetched';

                    articleDiv.innerHTML = `
                        <h3>${article.webTitle}</h3>
                        <p>${article.sectionName}</p>
                        <span class="${labelClass}">${labelText}</span><br>
                        <a href="${article.webUrl}" target="_blank" class="button-link">Read More</a>
                        <button class="save-article">Save Article</button>
                    `;

                    // Add save functionality
                    const saveButton = articleDiv.querySelector('.save-article');
                    saveButton.addEventListener('click', () => {
                        fetch('/save_article', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                webTitle: article.webTitle,
                                sectionName: article.sectionName,
                                webUrl: article.webUrl
                            })
                        })
                        .then(response => response.json())
                        .then(result => {
                            alert(result.message);
                        });
                    });

                    articlesDiv.appendChild(articleDiv);
                });
            });
    });
});


document.addEventListener('DOMContentLoaded', function () {
    if (window.location.pathname === '/saved_articles') {
        fetch('/get_saved_articles')
            .then(response => response.json())
            .then(articles => {
                const savedArticlesDiv = document.getElementById('saved-articles');
                savedArticlesDiv.innerHTML = ''; // Clear container to prevent duplication

                articles.forEach(article => {
                    const articleDiv = document.createElement('div');
                    articleDiv.classList.add('article-box'); // Add the article-box class for styling

                    articleDiv.innerHTML = `
                        <h3>${article.webTitle}</h3>
                        <p>${article.sectionName}</p>
                        <a href="${article.webUrl}" target="_blank" class="button-link">Read More</a>
                        <button class="delete-button" data-url="${article.webUrl}">Delete</button>
                    `;

                    const deleteButton = articleDiv.querySelector('.delete-button');
                    deleteButton.addEventListener('click', () => {
                        deleteArticle(article.webUrl);
                    });

                    savedArticlesDiv.appendChild(articleDiv);
                });
            });
    }
});

// Function to delete an article
function deleteArticle(articleUrl) {
    fetch('/delete_article', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: articleUrl })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Article deleted successfully');
            location.reload(); // Reload page to update the list of saved articles
        } else {
            alert('Failed to delete article: ' + data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}
