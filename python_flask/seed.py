import sqlite3
import random
from faker import Faker
from main import app, db, Author, Article

fake = Faker()

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///var/mock_data.sqlitedb"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

with app.app_context():
    db.drop_all()
    db.create_all()

    authors = []
    for i in range(10):
        author = Author(
            firstname=fake.first_name(),
            lastname=fake.last_name(),
        )
        authors.append(author)
        db.session.add(author)
    
    db.session.commit()

    titles_snippets = [
        ("The Future of Smartphones", "An overview of upcoming trends in smartphone design and AI integration."),
        ("5 Must-Visit Cities in Europe", "A travel guide to lesser-known but amazing European cities."),
        ("Quick Weeknight Dinners", "Simple and delicious dinner ideas for busy weeknights."),
        ("Top 10 Budgeting Tips", "How to manage your money better with these simple tips."),
        ("Championship Review: 2025", "A look back at the highlights of the 2025 championship season."),
        ("The Art of Storytelling", "How to captivate readers with compelling narratives."),
        ("Understanding Climate Change", "An explainer on the causes and impacts of global climate change."),
        ("Famous Historical Figures", "An in-depth look at people who shaped world history."),
        ("Minimalist Home Decor", "Tips for achieving a clean and stylish minimalist home aesthetic."),
        ("Nutrition Myths Busted", "Common misconceptions about food and healthy eating."),
        ("Best Hiking Trails in the US", "Explore scenic trails that are perfect for all skill levels."),
        ("AI in Everyday Life", "Examples of artificial intelligence applications in daily routines."),
        ("Healthy Desserts That Taste Great", "Satisfy your sweet tooth without the guilt."),
        ("The Science Behind Sports Injuries", "Understanding common sports injuries and prevention techniques."),
        ("Mastering Dialogue in Fiction", "How to write realistic and engaging conversations in your stories."),
        ("Investing for Beginners", "A straightforward guide to getting started with investing."),
        ("How Artists Find Inspiration", "A peek into the creative processes of modern artists."),
        ("Holistic Approaches to Wellness", "Exploring alternative and complementary health practices."),
        ("Urban Sustainability Projects", "City-level initiatives making a difference in the environment."),
        ("Writing Historical Fiction", "Tips for blending fact and fiction in historical novels."),
        ("Best Free Museums in the World", "Cultural treasures you can explore without spending a dime."),
        ("The Rise of Foldable Tech", "How foldable devices are changing the tech landscape."),
        ("Comfort Food with a Healthy Twist", "Classic comfort dishes made healthier with smart substitutions."),
        ("The Comeback of Retro Jerseys", "Why vintage sportswear is trending again."),
        ("Crafting a Compelling Plot", "Plot structures that keep readers hooked."),
        ("Saving for Retirement", "Strategies to help you build a comfortable retirement fund."),
        ("Color Psychology in Design", "How color influences mood and design choices."),
        ("The Power of Preventive Care", "Why regular checkups and screenings are crucial."),
        ("Documentaries That Changed History", "Films that brought important stories to light."),
        ("Weekend Getaways Near You", "Short trips that offer a big break from routine.")
    ]

    # Shuffle and assign articles to authors (1-3 authors per article)
    random.shuffle(titles_snippets)
    for title, snippet in titles_snippets:
        # Create article
        article = Article(
            title=title,
            #snippet=snippet # Uncomment the following line when you are ready to add a snippet to the article

            # Comment the following line when you are ready to assign multiple authors to an article
            author_id=random.choice(authors).id
        )
        db.session.add(article)
        
        # Assign 1-3 random authors to each article
        # Uncomment the following lines when you are ready to assign multiple authors to an article

        #num_authors = random.randint(1, 3)
        #selected_authors = random.sample(authors, num_authors)
        #article.authors = selected_authors

    db.session.commit()
    print("Database seeded successfully!")