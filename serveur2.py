# -*- coding: utf-8 -*-
"""
Created on Thu Jun  6 11:17:37 2019

@author: Raphaelle Debaecker
"""

import http.server
import socketserver
from urllib.parse import urlparse, parse_qs, unquote
import json

import matplotlib.pyplot as plt
import datetime as dt
import matplotlib.dates as pltd

import sqlite3


# On redéfinit le handler
class RequestHandler(http.server.SimpleHTTPRequestHandler):

  # On établit un répertoire pour les documents statiques
  static_dir = '/client'

  # On surcharge la méthode qui s'occupe des requêtes GET
  def do_GET(self):

    # On définit les étapes du chemin d'accès dans l'ordre suivant : 
    # on commence par /time, ensuite /regions et enfin /ponctualite
    
    self.init_params()

    if self.path_info[0] == 'time':
      self.send_time()

    elif self.path_info[0] == 'regions':
      self.send_regions()

    elif self.path_info[0] == 'ponctualite':
      self.send_ponctualite()

    else:
      self.send_static()


  # On surcharge la méthode qui s'occupe des requêtes HEAD
  def do_HEAD(self):
    self.send_static()

  # On définit une fonction qui renvoie le document statique
  def send_static(self):

    # On insère le répertoire préfixe dans le chemin d'accès
    self.path = self.static_dir + self.path

    # On utilise la méthode parent (do_GET / do_HEAD) par le verbe HTTP (GET / HEAD)
    if (self.command=='HEAD'):
        http.server.SimpleHTTPRequestHandler.do_HEAD(self)
    else:
        http.server.SimpleHTTPRequestHandler.do_GET(self)

  # On définit une fonction qui initialise les paramètres à partir des informations
  # recueillies par la requête (adresse, corps et traces)
  def init_params(self):
      
    # Adresse
    info = urlparse(self.path)
    
    

    
    
    self.path_info = [unquote(v) for v in info.path.split('/')[1:]]
    self.query_string = info.query
    self.params = parse_qs(info.query)

    # Corps
    length = self.headers.get('Content-Length')
    ctype = self.headers.get('Content-Type')
    if length:
      self.body = str(self.rfile.read(int(length)),'utf-8')
      if ctype == 'application/x-www-form-urlencoded' :
        self.params = parse_qs(self.body)
    else:
      self.body = ''

    # Traces
    print('info_path =',self.path_info)
    print('body =',length,ctype,self.body)
    print('params =', self.params)

  
  # On récupère l'heure pour envoyer un document au format html avec l'heure
  def send_time(self):

    time = self.date_time_string()
    body = '<!doctype html>' + \
           '<meta charset="utf-8">' + \
           '<title>l\'heure</title>' + \
           '<div>Voici l\'heure du serveur :</div>' + \
           '<pre>{}</pre>'.format(time)
    headers = [('Content-Type','text/html;charset=utf-8')]
    self.send(body,headers)

  
  # On constitue la liste des régions et de leurs coordonnées associées
  def send_regions(self):

    conn = sqlite3.connect('hydrometrie.sqlite')
    c = conn.cursor()

    c.execute("SELECT DISTINCT X, Y, LbStationHydro FROM 'StationHydro' JOIN 'hydrometrie_historique' ON CdStationHydroAncienRef = code_hydro")
    r = c.fetchall()

    headers = [('Content-Type','application/json')];
    body = json.dumps([{'nom':ligne[2], 'lat':ligne[1], 'lon': ligne[0]} for ligne in r])
    self.send(body,headers)

  
  # On constitue un graphe de ponctualité (en vérifiant que la région appelée existe, 
  # sinon on renvoie 'erreur 404')
  def send_ponctualite(self):
    print(self.path_info)
    conn = sqlite3.connect('hydrometrie.sqlite')
    c = conn.cursor()

    c.execute("SELECT DISTINCT LbStationHydro FROM 'hydrometrie_historique' JOIN 'StationHydro' ON CdStationHydroAncienRef = code_hydro")
    reg = c.fetchall()

    if (self.path_info[1],) in reg:
        regions = [(self.path_info[1],"red")]
    else:
        print ('Erreur nom')
        self.send_error(404)
        return None
    
    regions_selectionnees = self.path_info[9].split(',')
    
    if self.path_info[10]=='true': #cocher afficher toutes les station dans la même rivière
        station_ref=self.path_info[1]
        t = (station_ref,)
        c.execute("SELECT  CdEntiteHydrographique FROM 'StationHydro' WHERE LbStationHydro=?",t)#recherche riviere de la station de reference
        riv = c.fetchall()
        
        riviere= str(riv[0])[2:len(str(riv[0]))-3]
        riviere=(riviere,)
        c.execute("SELECT  DISTINCT LbStationHydro FROM 'StationHydro' WHERE CdEntiteHydrographique=?",riviere)#recherche station appartenent a la meme riviere que la station de reference
        reg_riv= c.fetchall()
        print('l149 station voisines:',regions)
        for i in reg_riv:
            a = str(i)[2:len(str(i))-3]
           
            if a != self.path_info[1]:
                regions_selectionnees.append(a)
        
       

    
    regions_selectionnees = list(set(regions_selectionnees))
    regions_selectionnees.sort()
    regions = [(i, 'red') for i in regions_selectionnees if (i,) in reg]
    
    print('l162 regions fianle',regions)

    donnees = {}
    donnees['xdeb'] = [] # Valeur de débit de x
    donnees['ydeb'] = [] # Valeur de débit de y
    donnees['xmoy'] = [] # Valeur moyenne de x
    donnees['ymoy'] = [] # Valeur moyenne de y
    donnees['xfor'] = [] # Valeur forte de x
    donnees['yfor'] = [] # Valeur forte de y
    donnees['nom_station'] = []

    if self.path_info[2] != '' and self.path_info[3] != '':
        debut_mois = int(self.path_info[3])
        debut_jour = int(self.path_info[2])
        debut_annee = int(self.path_info[4])
        fin_mois = int(self.path_info[6])
        fin_jour = int(self.path_info[5])
        fin_annee = int(self.path_info[7])

        debut_date = dt.date(debut_annee, debut_mois, debut_jour)
        fin_date = dt.date(fin_annee, fin_mois, fin_jour)

    c.execute("SELECT DISTINCT nomStat FROM Cache")
    reg2 = c.fetchall()


    

    for l in (regions) :
        if (self.path_info[1],) not in reg2:
           
            c.execute("SELECT * FROM 'hydrometrie_historique' JOIN 'StationHydro' ON CdStationHydroAncienRef = code_hydro WHERE LbStationHydro=? ORDER BY Date",l[:1])
            r = c.fetchall()

            self.collect_data(r, donnees, debut_date,fin_date, l[0], c, conn)

        self.get_data_from_cache(c, conn, debut_date, fin_date, l[0], donnees)


    # On récupère les données des trois fichiers fournis
    fichier1 = 'courbes/ponctualite_'+self.path_info[1] + '_debit.png'
    self.create_graphe(donnees['xdeb'], donnees['ydeb'], donnees['nom_station'], "Débit (en m^3) ", 'Débit de la station (en m^3) ', fichier1)

    fichier2 = 'courbes/ponctualite_'+self.path_info[1] + '_moyenne.png'
    self.create_graphe(donnees['xmoy'], donnees['ymoy'], donnees['nom_station'], "Moyenne interanuelle ", 'Moyenne interanuelle  (débit pentadaire médian) de la station ', fichier2)

    fichier3 = 'courbes/ponctualite_'+self.path_info[1] + '_valeur_forte.png'
    self.create_graphe(donnees['xfor'], donnees['yfor'], donnees['nom_station'], " Valeur forte ", 'Valeur forte (QJX quinquennal humide pour le mois considéré) de la station ', fichier3)

    body = json.dumps({
            'title': 'Diagrammes(s) associé(s) au(x) station(s) sélectionnée(s)', \
            'img1': '/'+fichier1, \
            'img2': '/'+fichier2, \
            'img3': '/'+fichier3 \
             });

    headers = [('Content-Type','application/json')];
    self.send(body,headers)
    
    # Si l'information est déjà dans le cache, on la récupère directement
  def get_data_from_cache(self, c, conn, debut_date, fin_date, nom, donnees):
       print(f" \n {nom} était déjà dans le cache, on récupère la data de la base de données \n" )
       xdeb = []
       ydeb = []
       xmoy = []
       ymoy = []
       xfor = []
       yfor = []

       debit = []
       moyenne = []
       valeur_forte = []

       debut_pltd = pltd.date2num(debut_date)
       fin_pltd = pltd.date2num(fin_date)
       c.execute("SELECT date, QJX, debit, moyenne FROM Cache WHERE date >= ? AND date <=? AND nomStat=?", (debut_pltd, fin_pltd, nom))
       data = c.fetchall()
       for l in data:
           if l[1] not in ["", None]:
               valeur_forte.append((l[0],float(l[1]) ))

           if l[2] not in ["", None]:
               debit.append((l[0],float(l[2]) ))

           if l[3] not in ["", None]:
               moyenne.append((l[0],float(l[3]) ))


       # Les dates sont triées pour que les points s'affichent dans le bon ordre
       debit.sort()
       moyenne.sort()
       valeur_forte.sort()

       for i in range(len(debit)):
           xdeb.append(debit[i][0])
           ydeb.append(debit[i][1])
           xmoy.append(moyenne[i][0])
           ymoy.append(moyenne[i][1])
           xfor.append(valeur_forte[i][0])
           yfor.append(valeur_forte[i][1])

       donnees['xdeb'].append(xdeb)
       donnees['ydeb'].append(ydeb) 
       donnees['xmoy'].append(xmoy) 
       donnees['ymoy'].append(ymoy)
       donnees['xfor'].append(xfor) 
       donnees['yfor'].append(yfor) 
       donnees['nom_station'].append(nom)


    # Si l'information n'est pas dans le cache, on met à jour la base de données avec les données
  def collect_data(self, raw_data, donnees, debut_date, fin_date, nom, c, conn):
      print(f" \n {nom} n'était pas dans le cache, on rajoute la data dans la base de données \n" )
      xdeb = []
      ydeb = []
      xmoy = []
      ymoy = []
      xfor = []
      yfor = []
      for a in raw_data:
          date = dt.date(int(a[2][:4]),int(a[2][5:7]),int(a[2][8:]))
          
          QJX, debit, moyenne = a[6], a[9], a[3]
          reference = (nom, pltd.date2num(date), QJX, debit, moyenne)
          c.execute("""INSERT INTO Cache(nomStat, date, QJX, debit, moyenne) VALUES(?, ?, ?, ?, ?)""", reference)

      conn.commit()


    # On trace la courbe et on aménage le graphique correspondant
  def create_graphe(self, liste_x,liste_y, liste_noms, titre_axe_y, titre_graphe, titre_fichier):
    fig1 = plt.figure(figsize=(18,6))
    ax = fig1.add_subplot(111)
    ax.grid(which='major', color='#888888', linestyle='-')
    ax.grid(which='minor',axis='x', color='#888888', linestyle=':')
    ax.xaxis.set_minor_locator(pltd.YearLocator())
    ax.xaxis.set_major_locator(pltd.MonthLocator())
    ax.xaxis.set_major_formatter(pltd.DateFormatter('%B %Y'))
    ax.xaxis.set_tick_params(labelsize=8)
    ax.xaxis.set_label_text("Date")
    ax.yaxis.set_label_text(titre_axe_y)

    for i in range(len(liste_x)):
        x = liste_x[i]
        y = liste_y[i]
        nom = liste_noms[i]
        plt.plot(x,y,linewidth=1, linestyle='-', marker='o', label=nom)

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width, box.height])

    ax.legend(loc='upper right')
    plt.title(titre_graphe,fontsize=16)

    plt.savefig('client/{}'.format(titre_fichier))
    plt.close()


  # On transmet les entêtes et le corps : on encode la chaîne de caractères, on transmet
  # la ligne de statut, on transmet les lignes d'entête et la ligne vide et on envoie le code
  # de la réponse
  def send(self,body,headers=[]):
    encoded = bytes(body, 'UTF-8')
    self.send_response(200)

    [self.send_header(*t) for t in headers]
    self.send_header('Content-Length',int(len(encoded)))
    self.end_headers()

    self.wfile.write(encoded)



# On instancie et on lance le serveur
httpd = socketserver.TCPServer(("", 8080), RequestHandler)
httpd.serve_forever()
