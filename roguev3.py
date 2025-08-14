import pgzrun,random,math
TITLE="Dungeon Escape"; WIDTH,HEIGHT=800,608
CELL=32; COLS,ROWS=20,19
STATE_MENU="menu"; STATE_GAME="game"; STATE_GAMEOVER="gameover"; STATE_WIN="win"
ENEMY_COUNT=5; ENEMY_TERRITORY_RADIUS=5
HERO_SPEED=6; ENEMY_SPEEDS=[3.5,4,4.5]
HERO_MAX_LIVES=3; HERO_INVULN=0.75
game_state=STATE_MENU; sound_enabled=True; music_started=False
LEVEL=[]; FLOOR=[]; hero=None; enemies=[]
start_pos=(0,0); key_pos=(0,0); exit_pos=(0,0)

def g2p(gx,gy): return gx*CELL,gy*CELL
def play_sound(n):
    if not sound_enabled: return
    try: getattr(sounds,n).play()
    except Exception as e: print("Sound warn",n,e)
def ensure_music():
    global music_started
    if sound_enabled and not music_started:
        try: music.play("bgm"); music_started=True
        except Exception as e: print("Music warn",e)
def stop_music():
    global music_started; music.stop(); music_started=False

def carve():
    g=[["#" for _ in range(COLS)] for _ in range(ROWS)]
    x=random.randint(1,COLS-2); y=random.randint(1,ROWS-2); g[y][x]="."
    for _ in range(COLS*ROWS*4):
        dx,dy=random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        nx,ny=x+dx,y+dy
        if 1<=nx<COLS-1 and 1<=ny<ROWS-1: x,y=nx,ny; g[ny][nx]="."
    floor=[(gx,gy) for gy in range(ROWS) for gx in range(COLS) if g[gy][gx]=="."]
    return (carve() if len(floor)<(COLS*ROWS)//6 else (g,floor))
def farthest(st,passable):
    vis={st:0}; q=[st]; i=0
    while i<len(q):
        cx,cy=q[i]; i+=1
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            n=(cx+dx,cy+dy)
            if n in passable and n not in vis:
                vis[n]=vis[(cx,cy)]+1; q.append(n)
    return max(vis.items(),key=lambda kv:kv[1])[0]
def gen_level():
    g,f=carve(); p=set(f)
    s=random.choice(f)
    k=farthest(s,p)             # chave longe do start
    e=farthest(k,p)             # saída longe da chave
    g[s[1]][s[0]]="S"; g[k[1]][k[0]]="K"; g[e[1]][e[0]]="E"
    return ["".join(r) for r in g],f,s,k,e
def is_wall(gx,gy): return not(0<=gx<COLS and 0<=gy<ROWS) or LEVEL[gy][gx]=="#"

class SpriteAnim:
    def __init__(self,idle,walk,fps=8):
        self.idle=idle; self.walk=walk; self.fps=fps
        self.t=0; self.i=0; self.moving=False; self.dir="down"
    def set_dir(self,d):
        if d!=self.dir: self.dir=d; self.i=0; self.t=0
    def frames(self): return self.walk[self.dir] if self.moving else self.idle
    def tick(self,dt):
        fr=self.frames()
        if len(fr)>1:
            self.t+=dt
            if self.t>=1/self.fps: self.t-=1/self.fps; self.i=(self.i+1)%len(fr)
    def image(self): return self.frames()[self.i]

class GridMover:
    def __init__(self,gx,gy,speed):
        self.gx=gx; self.gy=gy; self.tx=gx; self.ty=gy
        self.x,self.y=g2p(gx,gy); self.moving=False; self.speed=speed*CELL
    def want(self,dx,dy):
        if self.moving: return
        nx,ny=self.gx+dx,self.gy+dy
        if not is_wall(nx,ny): self.tx,self.ty=nx,ny; self.moving=True
    def update(self,dt):
        if not self.moving: return
        tx,ty=g2p(self.tx,self.ty); vx,vy=tx-self.x,ty-self.y
        d=math.hypot(vx,vy); step=self.speed*dt
        if d<=step: self.x,self.y=tx,ty; self.gx,self.gy=self.tx,self.ty; self.moving=False
        else: self.x+=vx/d*step; self.y+=vy/d*step

class Hero:
    def __init__(self,gx,gy):
        self.move=GridMover(gx,gy,HERO_SPEED)
        self.anim=SpriteAnim(
            ["hero_idle_0","hero_idle_1"],
            {"up":["hero_up_0","hero_up_1"],"down":["hero_down_0","hero_down_1"],
             "left":["hero_left_0","hero_left_1"],"right":["hero_right_0","hero_right_1"]},8)
        self.lives=HERO_MAX_LIVES; self.inv=0; self.has_key=False
    def update(self,dt):
        if self.inv>0: self.inv=max(0,self.inv-dt)
        dx=dy=0
        if not self.move.moving:
            if keyboard.w or keyboard.up: dy=-1; self.anim.set_dir("up")
            elif keyboard.s or keyboard.down: dy=1; self.anim.set_dir("down")
            elif keyboard.a or keyboard.left: dx=-1; self.anim.set_dir("left")
            elif keyboard.d or keyboard.right: dx=1; self.anim.set_dir("right")
            if dx or dy: self.move.want(dx,dy)
        self.move.update(dt); self.anim.moving=self.move.moving; self.anim.tick(dt)
    def hit(self):
        if self.inv>0: return
        self.lives-=1; self.inv=HERO_INVULN; play_sound("hit")
    def draw(self):
        if self.inv>0 and int(self.inv*20)%2==0: return
        screen.blit(self.anim.image(),(self.move.x,self.move.y))

class Enemy:
    def __init__(self,gx,gy,patrol,speed):
        self.move=GridMover(gx,gy,speed); self.patrol=patrol
        self.pref=random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.anim=SpriteAnim(
            ["slime_idle_0","slime_idle_1"],
            {"up":["slime_up_0","slime_up_1"],"down":["slime_down_0","slime_down_1"],
             "left":["slime_left_0","slime_left_1"],"right":["slime_right_0","slime_right_1"]},6)
    def update(self,dt):
        if not self.move.moving:
            dirs=[self.pref]+[(1,0),(-1,0),(0,1),(0,-1)]; random.shuffle(dirs)
            for dx,dy in dirs:
                nx,ny=self.move.gx+dx,self.move.gy+dy
                if not is_wall(nx,ny) and self.patrol[0]<=nx<=self.patrol[1] and self.patrol[2]<=ny<=self.patrol[3]:
                    self.pref=(dx,dy)
                    if dx==1:self.anim.set_dir("right")
                    elif dx==-1:self.anim.set_dir("left")
                    elif dy==1:self.anim.set_dir("down")
                    else:self.anim.set_dir("up")
                    self.move.want(dx,dy); break
        self.move.update(dt); self.anim.moving=self.move.moving; self.anim.tick(dt)
    def draw(self): screen.blit(self.anim.image(),(self.move.x,self.move.y))

class Button:
    def __init__(self,text,x,y,w,h,fn): self.text=text; self.x=x; self.y=y; self.w=w; self.h=h; self.fn=fn
    def draw(self):
        screen.draw.filled_rect(Rect((self.x,self.y),(self.w,self.h)),(50,50,70))
        screen.draw.text(self.text,center=(self.x+self.w//2,self.y+self.h//2),fontsize=36,color="white")
    def click(self,pos):
        if self.x<=pos[0]<=self.x+self.w and self.y<=pos[1]<=self.y+self.h: self.fn()

def build_enemies():
    pts=[c for c in FLOOR if c not in (start_pos,key_pos,exit_pos)]
    random.shuffle(pts); out=[]
    for i in range(min(ENEMY_COUNT,len(pts))):
        gx,gy=pts[i]
        area=(max(1,gx-ENEMY_TERRITORY_RADIUS),min(COLS-2,gx+ENEMY_TERRITORY_RADIUS),
              max(1,gy-ENEMY_TERRITORY_RADIUS),min(ROWS-2,gy+ENEMY_TERRITORY_RADIUS))
        out.append(Enemy(gx,gy,area,random.choice(ENEMY_SPEEDS)))
    return out

def start_game():
    global LEVEL,FLOOR,start_pos,key_pos,exit_pos,hero,enemies,game_state
    LEVEL,FLOOR,start_pos,key_pos,exit_pos=gen_level()
    hero=Hero(*start_pos); enemies=build_enemies(); game_state=STATE_GAME; ensure_music()
def toggle_sound():
    global sound_enabled
    sound_enabled=not sound_enabled
    if not sound_enabled: stop_music()
    else: ensure_music()
def exit_game(): stop_music(); raise SystemExit

buttons=[
    Button("Start Game",WIDTH//2-140,220,280,60,start_game),
    Button("Sound ON/OFF",WIDTH//2-140,300,280,60,toggle_sound),
    Button("Exit",WIDTH//2-140,380,280,60,exit_game)
]

def update(dt):
    global game_state
    if game_state==STATE_MENU: ensure_music(); return
    if game_state!=STATE_GAME: return
    hero.update(dt); [e.update(dt) for e in enemies]
    # pegar chave
    if not hero.has_key and (hero.move.gx,hero.move.gy)==key_pos:
        hero.has_key=True; play_sound("pickup") if "pickup" in dir(sounds) else None
    # colisão inimigos
    for e in enemies:
        if (hero.move.gx,hero.move.gy)==(e.move.gx,e.move.gy):
            hero.hit()
            if hero.lives<=0: game_state=STATE_GAMEOVER
            break
    # vitória exige chave
    if hero.has_key and (hero.move.gx,hero.move.gy)==exit_pos:
        game_state=STATE_WIN; play_sound("win")

def draw():
    screen.clear()
    if game_state==STATE_MENU: draw_menu()
    else:
        draw_level(); draw_hud(); hero.draw(); [e.draw() for e in enemies]
        if game_state==STATE_GAMEOVER: overlay("GAME OVER - Click")
        elif game_state==STATE_WIN: overlay("YOU WIN - Click")

def draw_menu():
    screen.fill((15,15,28))
    screen.draw.text("Dungeon Escape",center=(WIDTH//2,120),fontsize=64,color="white")
    for b in buttons: b.draw()
    screen.draw.text("Collect the key (K) then reach exit (E).",center=(WIDTH//2,500),fontsize=26,color="gray")

def draw_level():
    for gy,row in enumerate(LEVEL):
        for gx,c in enumerate(row):
            x,y=g2p(gx,gy)
            screen.draw.filled_rect(Rect((x,y),(CELL,CELL)),(40,40,60) if c=="#" else (22,22,32))
            if (gx,gy)==start_pos: screen.draw.text("S",center=(x+CELL//2,y+CELL//2),color="cyan",fontsize=22)
            if (gx,gy)==key_pos and not hero.has_key: screen.draw.text("K",center=(x+CELL//2,y+CELL//2),color="orange",fontsize=24)
            if (gx,gy)==exit_pos: screen.draw.text("E",center=(x+CELL//2,y+CELL//2),color="yellow",fontsize=24)

def draw_hud():
    screen.draw.text(f"Lives:{hero.lives}/{HERO_MAX_LIVES}  Key:{'YES' if hero.has_key else 'NO'}  Sound:{'ON' if sound_enabled else 'OFF'}",
                     (10,8),fontsize=22,color="white")
def overlay(msg):
    screen.draw.filled_rect(Rect((0,0),(WIDTH,HEIGHT)),(0,0,0))
    screen.draw.text(msg,center=(WIDTH//2,HEIGHT//2),fontsize=48,color="white")

def on_mouse_down(pos):
    global game_state
    if game_state==STATE_MENU:
        for b in buttons: b.click(pos)
    elif game_state in (STATE_GAMEOVER,STATE_WIN):
        game_state = STATE_MENU

pgzrun.go()