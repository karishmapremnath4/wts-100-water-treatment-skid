function make_pid
% MAKE_PID  WTS-100 Piping and Instrumentation Diagram (ISA-5.1)
%
%   Draws the P&ID for the WTS-100 water treatment and transfer skid and
%   exports it as pid.png and pid.pdf beside this file.
%
%   Run:  make_pid
%
%   Coordinates below are given with y increasing DOWNWARD, which is how
%   drawings are dimensioned. yy() flips them for MATLAB axes.
%
%   K. Premnath, August 2026

W = 1640; H = 1010; OX = 34; OY = 52;

fig = figure('Color','w','Units','pixels','Position',[60 60 W H], ...
             'MenuBar','none','ToolBar','none','Name','WTS-100 P&ID');
ax  = axes(fig,'Position',[0 0 1 1]); %#ok<LAXES>
hold(ax,'on'); axis(ax,'equal'); axis(ax,'off');
xlim(ax,[0 W]); ylim(ax,[0 H]);
set(ax,'Clipping','off');

S.ax = ax; S.H = H; S.ox = OX; S.oy = OY;

%% ------------------------------------------------------------------ FRAME
rectangle(ax,'Position',[12 12 W-24 H-24],'EdgeColor','k','LineWidth',0.6);
rectangle(ax,'Position',[30 30 W-60 H-60],'EdgeColor','k','LineWidth',1.2);

cols = 8; rows = 5;
cw = (W-60)/cols; rh = (H-60)/rows;
for i = 1:cols
    cx = 30 + cw*(i-0.5);
    text(ax,cx,H-21,sprintf('%d',i),'HorizontalAlignment','center','FontSize',8,'FontWeight','bold');
    text(ax,cx,21,   sprintf('%d',i),'HorizontalAlignment','center','FontSize',8,'FontWeight','bold');
    if i > 1
        x = 30 + cw*(i-1);
        line(ax,[x x],[H-12 H-30],'Color','k','LineWidth',0.6);
        line(ax,[x x],[12 30],    'Color','k','LineWidth',0.6);
    end
end
for i = 1:rows
    cy = H - (30 + rh*(i-0.5));
    text(ax,21,   cy,char(64+i),'HorizontalAlignment','center','FontSize',8,'FontWeight','bold');
    text(ax,W-21, cy,char(64+i),'HorizontalAlignment','center','FontSize',8,'FontWeight','bold');
    if i > 1
        y = H - (30 + rh*(i-1));
        line(ax,[12 30],  [y y],'Color','k','LineWidth',0.6);
        line(ax,[W-30 W-12],[y y],'Color','k','LineWidth',0.6);
    end
end

%% ------------------------------------------------- CONTROL ROOM / FIELD
CY = 78;
bubbleS(S,470,CY,'FIC','101'); bubbleS(S,770,CY,'LIC','102');
bubbleS(S,980,CY,'TIC','102'); bubbleS(S,1180,CY,'FFIC','103');
sline(S,[120 CY+52; 1440 CY+52]);
txt(S,126,CY+46,'CONTROL ROOM','left',8,'bold');
txt(S,126,CY+68,'FIELD','left',8,'bold');

%% ------------------------------------------------------------ T-101 AREA
vessel(S,70,250,150,210,'T-101','Raw Water Tank',178);
bubble(S,110,178,'LT','101',23);  sline(S,[110 201; 110 250]);
bubble(S,45,490,'LSLL','101',23); sline(S,[45 467; 45 430; 70 430]);

pline(S,[220 360; 245 360],false);
pline(S,[245 360; 245 300; 300 300],false);
pline(S,[245 360; 245 420; 300 420],false);
hvalve(S,270,300,'V-101A'); hvalve(S,270,420,'V-101B');
pump(S,324,300,'P-101A','Raw Water Duty');
pump(S,324,420,'P-101B','Raw Water Standby');
checkv(S,370,300,'NRV-101A'); checkv(S,370,420,'NRV-101B');
hvalve(S,400,300,'V-102A');   hvalve(S,400,420,'V-102B');
pline(S,[348 300; 420 300; 420 360],false);
pline(S,[348 420; 420 420; 420 360],false);
pline(S,[420 360; 430 360],false);
bubble(S,392,214,'PT','101',23); sline(S,[392 237; 392 300]);

%% --------------------------------------------------- FLOW ELEMENT, VALVES
sqbox(S,430,345,30,30,'M');
bubble(S,445,214,'FT','101',23); sline(S,[445 237; 445 345]);
pline(S,[460 360; 540 360],false);
ctrlvalve(S,556,360,'FCV-101');
pline(S,[572 360; 640 360],false);
hvalveL(S,656,360,'XV-101');
sqbox(S,644,316,24,18,'S');
sline(S,[656 316; 656 276]);
bubble(S,580,452,'ZSO','101',20); sline(S,[580 432; 580 404; 644 404; 644 374]);
bubble(S,660,452,'ZSC','101',20); sline(S,[660 432; 660 374]);
pline(S,[672 360; 760 360; 760 300],true);

%% ------------------------------------------------------------ T-102 AREA
vessel(S,700,300,230,250,'T-102','Treatment Tank',825);
heater(S);
tags = {'LSHH','102';'LT','102';'TT','102';'TSHH','102'};
ys   = [330 400 470 540];
for k = 1:4
    bubble(S,960,ys(k),tags{k,1},tags{k,2},23);
    sline(S,[937 ys(k); 930 ys(k)]);
end
pline(S,[715 300; 715 278],false);
relief(S,715,268,'PSV-102');
pline(S,[715 250; 715 226],true);
txt(S,723,230,'NOTE 3','left',8,'normal');

%% -------------------------------------------------------------- DOSING
vessel(S,700,626,110,130,'T-103','Chemical',755);
pline(S,[810 696; 860 696],false);
pump(S,884,696,'P-103','Dosing Pump');
pline(S,[908 696; 960 696],false);
sqbox(S,960,681,30,30,'C');
bubble(S,1060,696,'FT','103',23); sline(S,[1037 696; 990 696]);
pline(S,[990 696; 1360 696; 1360 240; 890 240; 890 300],true);

%% ------------------------------------------------------------ DISCHARGE
pline(S,[880 550; 880 590; 1010 590],false);
hvalveL(S,1026,590,'XV-102');
sqbox(S,1014,546,24,18,'S');
sline(S,[1026 546; 1026 520]);
pline(S,[1042 590; 1090 590],false);
pump(S,1114,590,'P-102','Discharge Pump');
sline(S,[1114 566; 1114 520]);
pline(S,[1138 590; 1250 590],true);
txt(S,1196,572,'TO STORAGE','center',9,'bold');
bubble(S,1160,470,'AT','102',23); sline(S,[1160 493; 1160 590]);

%% --------------------------------------------------------- SIGNAL WIRING
sline(S,[445 191; 445 150; 470 150; 470 103]);
sline(S,[470 53; 470 30; 556 30; 556 326]);
sline(S,[960 377; 1010 377; 1010 150; 770 150; 770 103]);
sline(S,[770 53; 770 20; 430 20; 430 150; 452 150]);
sline(S,[960 447; 1040 447; 1040 140; 980 140; 980 103]);
sline(S,[980 53; 1000 53; 1000 40; 880 40; 880 455; 820 455; 820 470]);
sline(S,[1060 673; 1060 636; 1180 636; 1180 103]);
sline(S,[1180 53; 1320 53; 1320 616; 884 616; 884 672]);
sline(S,[1160 447; 1160 300; 1236 300]);
txt(S,1244,304,'NOTE 4','left',8,'normal');
sline(S,[445 168; 1128 168; 1128 78; 1155 78]);
plot(S.ax,445+OX,yy(S,168),'k.','MarkerSize',7);

%% ------------------------------------------------------------ LINE NUMBERS
txt(S,262,344,'50-WA-101','center',7.5,'bold');
txt(S,500,343,'50-WA-102','center',7.5,'bold');
txt(S,945,573,'50-WA-103','center',7.5,'bold');
txt(S,925,677,'15-CH-101','center',7.5,'bold');

%% ------------------------------------------------------------ NOTES BOX
nx = 40; ny = 856; nw = 520; nh = 122;
rectangle(ax,'Position',[nx H-ny-nh nw nh],'EdgeColor','k','LineWidth',1);
line(ax,[nx nx+nw],[H-ny-20 H-ny-20],'Color','k','LineWidth',1);
text(ax,nx+8,H-ny-14,'NOTES','FontSize',7.5,'FontWeight','bold','HorizontalAlignment','left');
notes = { '1.  ALL INSTRUMENTS 4-20 mA UNLESS NOTED.', ...
          '2.  SAFETY CONTACTS WIRED NORMALLY CLOSED. DE-ENERGISE TO TRIP.', ...
          '3.  PSV-102 DISCHARGE TO SAFE LOCATION.', ...
          '4.  AT-102 SIGNAL TO HISTORIAN.', ...
          '5.  DRAWING SCOPED TO CONTROL SYSTEM. INSTRUMENT ROOT VALVES,', ...
          '     DRAINS AND PIPE SPECIFICATIONS NOT SHOWN.' };
for k = 1:numel(notes)
    text(ax,nx+8,H-ny-36-(k-1)*16,notes{k},'FontSize',7,'HorizontalAlignment','left');
end

%% ------------------------------------------------------------ LEGEND BOX
lx = 578; nw2 = 500;
rectangle(ax,'Position',[lx H-ny-nh nw2 nh],'EdgeColor','k','LineWidth',1);
line(ax,[lx lx+nw2],[H-ny-20 H-ny-20],'Color','k','LineWidth',1);
text(ax,lx+8,H-ny-14,'LEGEND','FontSize',7.5,'FontWeight','bold','HorizontalAlignment','left');
line(ax,[lx+14 lx+70],[H-ny-40 H-ny-40],'Color','k','LineWidth',1.8);
text(ax,lx+80,H-ny-40,'PROCESS LINE','FontSize',7,'HorizontalAlignment','left');
line(ax,[lx+14 lx+70],[H-ny-62 H-ny-62],'Color','k','LineWidth',0.7,'LineStyle','--');
text(ax,lx+80,H-ny-62,'ELECTRICAL SIGNAL','FontSize',7,'HorizontalAlignment','left');
rectangle(ax,'Position',[lx+29 H-ny-103 26 26],'Curvature',[1 1],'EdgeColor','k','FaceColor','w','LineWidth',1);
line(ax,[lx+29 lx+55],[H-ny-90 H-ny-90],'Color','k','LineWidth',0.7);
text(ax,lx+80,H-ny-88,'FIELD MOUNTED INSTRUMENT','FontSize',7,'HorizontalAlignment','left');
rectangle(ax,'Position',[lx+245 H-ny-103 26 26],'EdgeColor','k','FaceColor','w','LineWidth',1);
rectangle(ax,'Position',[lx+245 H-ny-103 26 26],'Curvature',[1 1],'EdgeColor','k','FaceColor','w','LineWidth',1);
line(ax,[lx+245 lx+271],[H-ny-90 H-ny-90],'Color','k','LineWidth',0.7);
text(ax,lx+296,H-ny-84,'CONTROL ROOM','FontSize',7,'HorizontalAlignment','left');
text(ax,lx+296,H-ny-96,'SHARED DISPLAY','FontSize',7,'HorizontalAlignment','left');
text(ax,lx+14,H-ny-116,'S = SOLENOID    M = MAGNETIC FLOWMETER    C = CORIOLIS FLOWMETER', ...
     'FontSize',7,'HorizontalAlignment','left');

%% -------------------------------------------------------- TITLE BLOCK
tx = 1096; tw = 504;
rectangle(ax,'Position',[tx H-ny-nh tw nh],'EdgeColor','k','LineWidth',1.2);
for yy_ = [42 72 97]
    line(ax,[tx tx+tw],[H-ny-yy_ H-ny-yy_],'Color','k','LineWidth',0.7);
end
line(ax,[tx+300 tx+300],[H-ny-72 H-ny-nh],'Color','k','LineWidth',0.7);
line(ax,[tx+400 tx+400],[H-ny-72 H-ny-nh],'Color','k','LineWidth',0.7);
line(ax,[tx+150 tx+150],[H-ny-97 H-ny-nh],'Color','k','LineWidth',0.7);
tb(ax,tx+10, H-ny-20, 'PROJECT',6.5,'normal');
tb(ax,tx+10, H-ny-36, 'WTS-100  WATER TREATMENT AND TRANSFER SKID',11,'bold');
tb(ax,tx+10, H-ny-56, 'TITLE',6.5,'normal');
tb(ax,tx+70, H-ny-57, 'PIPING AND INSTRUMENTATION DIAGRAM',8.5,'bold');
tb(ax,tx+10, H-ny-84, 'DRAWING No',6.5,'normal');
tb(ax,tx+10, H-ny-94, 'WTS-100-PID-001',8.5,'bold');
tb(ax,tx+310,H-ny-84, 'REV',6.5,'normal');    tb(ax,tx+310,H-ny-94,'A',8.5,'bold');
tb(ax,tx+410,H-ny-84, 'SHEET',6.5,'normal');  tb(ax,tx+410,H-ny-94,'1 OF 1',8.5,'bold');
tb(ax,tx+10, H-ny-110,'DRAWN',6.5,'normal');  tb(ax,tx+60, H-ny-111,'K. PREMNATH',8.5,'bold');
tb(ax,tx+160,H-ny-110,'CHECKED',6.5,'normal');
tb(ax,tx+310,H-ny-110,'SCALE',6.5,'normal');  tb(ax,tx+350,H-ny-111,'NTS',8.5,'bold');
tb(ax,tx+410,H-ny-110,'DATE',6.5,'normal');   tb(ax,tx+445,H-ny-111,'AUG 2026',8.5,'bold');

%% ------------------------------------------------------------- EXPORT
here = fileparts(mfilename('fullpath'));
exportgraphics(ax, fullfile(here,'pid.png'), 'Resolution', 150);
exportgraphics(ax, fullfile(here,'pid.pdf'), 'ContentType','vector');
fprintf('wrote pid.png and pid.pdf\n');
end

%% ===================================================== helper functions
function v = yy(S,y),  v = S.H - (y + S.oy); end
function v = xx(S,x),  v = x + S.ox;         end

function txt(S,x,y,str,align,fs,wt)
    text(S.ax,xx(S,x),yy(S,y),str,'HorizontalAlignment',align, ...
         'FontSize',fs,'FontWeight',wt,'Interpreter','none');
end

function tb(ax,x,y,str,fs,wt)
    text(ax,x,y,str,'HorizontalAlignment','left','FontSize',fs, ...
         'FontWeight',wt,'Interpreter','none');
end

function pline(S,pts,arrowEnd)
    X = xx(S,pts(:,1)); Y = yy(S,pts(:,2));
    line(S.ax,X,Y,'Color','k','LineWidth',1.6);
    if nargin>2 && arrowEnd, arrowhead(S,pts(end-1,:),pts(end,:)); end
end

function sline(S,pts)
    X = xx(S,pts(:,1)); Y = yy(S,pts(:,2));
    line(S.ax,X,Y,'Color','k','LineWidth',0.7,'LineStyle','--');
end

function arrowhead(S,p1,p2)
    d = p2 - p1; n = norm(d); if n==0, return; end
    u = d/n; p = [-u(2) u(1)]; L = 11; Wd = 4.5;
    tip = p2; b = p2 - u*L;
    X = [tip(1) b(1)+p(1)*Wd b(1)-p(1)*Wd];
    Y = [tip(2) b(2)+p(2)*Wd b(2)-p(2)*Wd];
    patch(S.ax,'XData',xx(S,X),'YData',yy(S,Y),'FaceColor','k','EdgeColor','k');
end

function vessel(S,x,y,w,h,tag,name,lx)
    rectangle(S.ax,'Position',[xx(S,x) yy(S,y+h) w h],'EdgeColor','k','LineWidth',1.4);
    txt(S,lx,y-24,tag,'center',9,'bold');
    txt(S,lx,y-10,name,'center',7,'normal');
end

function bubble(S,cx,cy,top,bot,r)
    rectangle(S.ax,'Position',[xx(S,cx)-r yy(S,cy)-r 2*r 2*r],'Curvature',[1 1], ...
              'EdgeColor','k','FaceColor','w','LineWidth',1.2);
    line(S.ax,[xx(S,cx)-r xx(S,cx)+r],[yy(S,cy) yy(S,cy)],'Color','k','LineWidth',0.7);
    txt(S,cx,cy-5,top,'center',8,'bold');
    txt(S,cx,cy+13,bot,'center',8,'bold');
end

function bubbleS(S,cx,cy,top,bot)
    r = 25;
    rectangle(S.ax,'Position',[xx(S,cx)-r yy(S,cy)-r 2*r 2*r],'EdgeColor','k','FaceColor','w','LineWidth',1.2);
    bubble(S,cx,cy,top,bot,r);
end

function pump(S,cx,cy,tag,name)
    r = 24;
    rectangle(S.ax,'Position',[xx(S,cx)-r yy(S,cy)-r 2*r 2*r],'Curvature',[1 1], ...
              'EdgeColor','k','FaceColor','w','LineWidth',1.4);
    X = [cx-10 cx-10 cx+15]; Y = [cy-13 cy+13 cy];
    patch(S.ax,'XData',xx(S,X),'YData',yy(S,Y),'FaceColor','k','EdgeColor','k');
    txt(S,cx,cy+40,tag,'center',8.5,'bold');
    txt(S,cx,cy+53,name,'center',7,'normal');
end

function bowtie(S,cx,cy,hw,hh)
    X = [cx-hw cx-hw cx+hw cx+hw]; Y = [cy-hh cy+hh cy-hh cy+hh];
    patch(S.ax,'XData',xx(S,X),'YData',yy(S,Y),'FaceColor','w','EdgeColor','k','LineWidth',1.2);
end

function hvalve(S,cx,cy,tag)
    bowtie(S,cx,cy,9,10);  txt(S,cx,cy+24,tag,'center',7,'bold');
end

function hvalveL(S,cx,cy,tag)
    bowtie(S,cx,cy,16,13); txt(S,cx,cy+32,tag,'center',8.5,'bold');
end

function ctrlvalve(S,cx,cy,tag)
    bowtie(S,cx,cy,16,13);
    th = linspace(pi,0,24); ax_ = xx(S,cx)+13*cos(th); ay = yy(S,cy+16)+18*sin(th);
    patch(S.ax,'XData',ax_,'YData',ay,'FaceColor','w','EdgeColor','k','LineWidth',1.2);
    line(S.ax,[xx(S,cx) xx(S,cx)],[yy(S,cy-16) yy(S,cy-25)],'Color','k','LineWidth',1.2);
    txt(S,cx,cy+32,tag,'center',8.5,'bold');
end

function checkv(S,cx,cy,tag)
    bowtie(S,cx,cy,9,10);
    line(S.ax,[xx(S,cx+9) xx(S,cx+9)],[yy(S,cy-12) yy(S,cy+12)],'Color','k','LineWidth',1.6);
    txt(S,cx,cy-16,tag,'center',7,'bold');
end

function relief(S,cx,cy,tag)
    X = [cx-10 cx+10 cx+10 cx-10]; Y = [cy+10 cy+10 cy-8 cy-8];
    patch(S.ax,'XData',xx(S,X),'YData',yy(S,Y),'FaceColor','w','EdgeColor','k','LineWidth',1.2);
    zx = cx + [0 -6 6 -6 6]; zy = cy + [-8 -13 -18 -23 -28];
    line(S.ax,xx(S,zx),yy(S,zy),'Color','k','LineWidth',1.2);
    txt(S,cx+16,cy-2,tag,'left',7,'bold');
end

function sqbox(S,x,y,w,h,label)
    rectangle(S.ax,'Position',[xx(S,x) yy(S,y+h) w h],'EdgeColor','k','FaceColor','w','LineWidth',1.2);
    txt(S,x+w/2,y+h/2+4,label,'center',8.5,'bold');
end

function heater(S)
    hx = [730 730 760 760 790 790 820];
    hy = [500 470 470 500 500 470 470];
    line(S.ax,xx(S,hx),yy(S,hy),'Color','k','LineWidth',1.8);
    txt(S,775,520,'HTR-101','center',8.5,'bold');
    txt(S,775,533,'6 kW Immersion','center',7,'normal');
end
