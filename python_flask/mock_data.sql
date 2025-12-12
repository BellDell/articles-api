BEGIN TRANSACTION;
CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    title TEXT,
    author_id INTEGER,
    snippet TEXT,
    FOREIGN KEY(author_id) REFERENCES authors(id)
);
INSERT INTO "articles" VALUES(1,'Holistic Approaches to Wellness',1,'Exploring alternative and complementary health practices.');
INSERT INTO "articles" VALUES(2,'Writing Historical Fiction',2,'Tips for blending fact and fiction in historical novels.');
INSERT INTO "articles" VALUES(3,'Crafting a Compelling Plot',2,'Plot structures that keep readers hooked.');
INSERT INTO "articles" VALUES(4,'Urban Sustainability Projects',2,'City-level initiatives making a difference in the environment.');
INSERT INTO "articles" VALUES(5,'The Science Behind Sports Injuries',2,'Understanding common sports injuries and prevention techniques.');
INSERT INTO "articles" VALUES(6,'Documentaries That Changed History',2,'Films that brought important stories to light.');
INSERT INTO "articles" VALUES(7,'5 Must-Visit Cities in Europe',2,'A travel guide to lesser-known but amazing European cities.');
INSERT INTO "articles" VALUES(8,'Color Psychology in Design',2,'How color influences mood and design choices.');
INSERT INTO "articles" VALUES(9,'The Power of Preventive Care',2,'Why regular checkups and screenings are crucial.');
INSERT INTO "articles" VALUES(10,'Minimalist Home Decor',2,'Tips for achieving a clean and stylish minimalist home aesthetic.');
INSERT INTO "articles" VALUES(11,'The Rise of Foldable Tech',3,'How foldable devices are changing the tech landscape.');
INSERT INTO "articles" VALUES(12,'Saving for Retirement',3,'Strategies to help you build a comfortable retirement fund.');
INSERT INTO "articles" VALUES(13,'The Art of Storytelling',3,'How to captivate readers with compelling narratives.');
INSERT INTO "articles" VALUES(14,'Quick Weeknight Dinners',3,'Simple and delicious dinner ideas for busy weeknights.');
INSERT INTO "articles" VALUES(15,'Famous Historical Figures',3,'An in-depth look at people who shaped world history.');
INSERT INTO "articles" VALUES(16,'Comfort Food with a Healthy Twist',3,'Classic comfort dishes made healthier with smart substitutions.');
INSERT INTO "articles" VALUES(17,'Weekend Getaways Near You',3,'Short trips that offer a big break from routine.');
INSERT INTO "articles" VALUES(18,'Mastering Dialogue in Fiction',4,'How to write realistic and engaging conversations in your stories.');
INSERT INTO "articles" VALUES(19,'Nutrition Myths Busted',4,'Common misconceptions about food and healthy eating.');
INSERT INTO "articles" VALUES(20,'The Future of Smartphones',4,'An overview of upcoming trends in smartphone design and AI integration.');
INSERT INTO "articles" VALUES(21,'The Comeback of Retro Jerseys',4,'Why vintage sportswear is trending again.');
INSERT INTO "articles" VALUES(22,'How Artists Find Inspiration',4,'A peek into the creative processes of modern artists.');
INSERT INTO "articles" VALUES(23,'Top 10 Budgeting Tips',4,'How to manage your money better with these simple tips.');
INSERT INTO "articles" VALUES(24,'Championship Review: 2025',4,'A look back at the highlights of the 2025 championship season.');
INSERT INTO "articles" VALUES(25,'Investing for Beginners',4,'A straightforward guide to getting started with investing.');
INSERT INTO "articles" VALUES(26,'Best Free Museums in the World',4,'Cultural treasures you can explore without spending a dime.');
INSERT INTO "articles" VALUES(27,'Best Hiking Trails in the US',4,'Explore scenic trails that are perfect for all skill levels.');
INSERT INTO "articles" VALUES(28,'Understanding Climate Change',5,'An explainer on the causes and impacts of global climate change.');
INSERT INTO "articles" VALUES(29,'Healthy Desserts That Taste Great',5,'Satisfy your sweet tooth without the guilt.');
INSERT INTO "articles" VALUES(30,'AI in Everyday Life',5,'Examples of artificial intelligence applications in daily routines.');
CREATE TABLE authors (
    id INTEGER PRIMARY KEY,
    firstname TEXT,
    lastname TEXT,
    bio TEXT
);
INSERT INTO "authors" VALUES(1,'Stephanie','Noble','a freelance writer covering travel and lifestyle topics.');
INSERT INTO "authors" VALUES(2,'Pamela','Lewis','writes about technology trends and gadget reviews.');
INSERT INTO "authors" VALUES(3,'Savannah','Lynch','a food blogger and cookbook author.');
INSERT INTO "authors" VALUES(4,'Amanda','Wilkins','covers environmental issues and sustainability.');
INSERT INTO "authors" VALUES(5,'James','Potts','writes fiction and creative writing guides.');
INSERT INTO "authors" VALUES(6,'Diane','Johnson','a sports columnist and commentator.');
INSERT INTO "authors" VALUES(7,'Javier','Hall','specializes in personal finance and budgeting.');
INSERT INTO "authors" VALUES(8,'Mary','Mcknight','writes historical articles and biographies.');
INSERT INTO "authors" VALUES(9,'Daniel','Howell','covers art and design.');
INSERT INTO "authors" VALUES(10,'Amy','Edwards','writes about health and wellness topics.');
COMMIT;