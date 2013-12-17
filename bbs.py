#coding=utf-8
'''Created on Dec 15, 2013 @author: Jesse MENG'''
import os.path
import torndb
import tornado.httpserver
import tornado.ioloop 
import tornado.web 
from tornado.options import parse_command_line
class BBS(tornado.web.Application):
    def __init__(self):
        handlers = [(r"/", LoginHandler),(r"/home",HomeHandler),(r"/login",LoginHandler), (r"/logout",LogoutHandler),
                    (r"/user/register",RegisterHandler),(r"/posts/create",PostCreateHandler),(r"/posts/(\d+)",PostDetailHandler)]
        settings = dict(blog_title=u"ZDYX BBS PYTHON VERSION",  
                        template_path=os.path.join(os.path.dirname(__file__), "template"),
                        static_path=os.path.join(os.path.dirname(__file__), "static"),
                        xsrf_cookies=True,cookie_secret="bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",login_url="login")
        tornado.web.Application.__init__(self, handlers, **settings)
        self.db = torndb.Connection(host="127.0.0.1:3306", database="bbs",user="root", password="")

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db
    def get_current_user(self):
        return self.get_secure_cookie("username")
        
class RegisterHandler(BaseHandler):
    def get(self):
        self.render("user/register.html", headtype="noauth")
    def post(self):
        username,password = self.get_argument("username"),self.get_argument("password")
        self.db.execute("INSERT INTO users(username, password, enabled) "
                        "VALUES (%s,%s,%s)",username,password,str(1))
        userid = self.db.get("select id from users where username = %s",username)['id']
        self.db.execute("INSERT INTO user_roles(userid, rolename) "
                        "VALUES (%s, %s)",userid,"ROLE_REGULAR")
        self.set_secure_cookie("username", username, 30)
        self.redirect("/login")
class LoginHandler(BaseHandler):
    def get(self): 
        if self.get_current_user(): 
            self.redirect("home")
            return
        self.render('login.html',headtype="noauth")
    def post(self):
        username,password = self.get_argument("username"),self.get_argument("password")
        results = self.db.query("select * from users") 
        for result in results:
            if result['username']==username and result['password']==password:
                self.set_secure_cookie("username", username)
                self.redirect("/home")
                return
        self.clear_cookie("username")
        self.redirect("/login")
class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("username")
        self.redirect("home")
    
class HomeHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        if not self.get_current_user(): 
            self.redirect("/login")
            return
        posts = self.db.query("SELECT * FROM post WHERE parent_id =0 ORDER BY create_time DESC") 
        self.render("home.html", posts=posts, headtype="auth")

class PostCreateHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("posts/create.html", headtype="auth")
    @tornado.web.authenticated
    def post(self):
        username=self.get_current_user()
        title,content,parentid = self.get_argument("title"),self.get_argument("content"),self.get_argument("parentId")
        postid = self.db.get("select id from users where username = %s",username)['id']
        self.db.execute("INSERT INTO post(parent_id,author_name,title,content,create_time,modify_time,creator_id,modifier_id,liked_times) "
                        "VALUES (%s, %s, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP(), %s, %s, %s)",parentid,username,title,content,postid,postid,str(0))
        if parentid == '0': self.redirect("/home")
        else: self.redirect("/posts/%s"%parentid)
class PostDetailHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self,num):
        posts=self.db.query("SELECT id,parent_id,author_name,title,content,create_time,modify_time,creator_id,modifier_id,liked_times FROM post "
                            "WHERE (id = %s and parent_id = 0) OR parent_id = %s ORDER BY id asc",num,num)
        self.render("posts/show.html",posts=posts,postid=num,posttitle=posts[0]['title'],headtype="auth")

def main(): 
    parse_command_line()
    http_server = tornado.httpserver.HTTPServer(BBS())
    http_server.bind(8421)
    http_server.start(num_processes=2)     
    tornado.ioloop.IOLoop.instance().start()
if __name__ == "__main__":
    main()
    