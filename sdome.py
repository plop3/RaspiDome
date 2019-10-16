#!/usr/bin/python3
# -*- encoding: utf8 -*-

# Pilotage automatique de l'abri du télescope.
# Serge CLAUS
# GPL V3
# Version 1.0.4
# 30/09/2019 - 14/10/2019
# Version python3 pour Raspberry PI

##### MODULES EXTERNES #####
import sys
import socketserver
import time
import threading
# Firmata
from pymata_aio.pymata3 import PyMata3
from pymata_aio.constants import Constants

from rpi_TM1638 import TMBoards

board = PyMata3(com_port='/dev/Firmata')
SERIAL="/dev/MySensors"

DEPLACEMENT=False
ARRETURG=False

# TM1638
DIO=19
CLK=13
STB=6

TM=TMBoards(DIO, CLK, STB, 0)

#Adresses I2c
#26 	LCD
#27		Clavier matriciel 4x4

APA=18		# LEDs néopixel
LCDBCK=4	# Rétro-éclairage LCD
BUZZER=22 	# ou 23 /!\ Pas de Pwm (1 seul canal dispo pour le backlight LCD)

# Entrées/sorties
AO=14	#A1 16
AF=15	#A0 17
Po1=16	#A2 18
Po2=18	#A3 20
Pf1=17	#A4 19
Pf2=19	#A5 21

PARK = 21	#A6

MOTEUR=11	#D11
ALIMMOT=10	#D10
ALIM12=9	#D9
ALIMTEL=8	#D8
P11=7		#D7
P12=6		#D6
P21=5		#D5
P22=4		#D4

# Délais
DPORTES=40
DPORTESCAPTEURS=30
DMOTEUR=40
DABRI=22

##### CLASSES #####
class ARUExcept(Exception):
	pass
	
##### FONCTIONS #####
def PStatus(pin):
	if pin<14:
		return board.get_pin_state(pin)[2]
	elif pin > 19:
		if board.analog_read(pin-14)> 300:
			return True
		else:
			return False
	else:
		return board.digital_read(pin)
def Pwrite(pin, etat):
	board.digital_write(pin, etat)
def Pinit(pin,mode):
	board.set_pin_mode(pin, mode)
		
def AlimStatus():
	return not PStatus(ALIMTEL)
def MoteurStatus():
	return not PStatus(ALIMMOT)
def StartTel():
	Pwrite(ALIMTEL,0)
def StopTel():
	Pwrite(ALIMTEL,1)
def StartMot():
	Pwrite(ALIMMOT,0)
def StopMot(): 
	Pwrite(ALIMMOT,1)
def PortesOuvert():
	return not PStatus(Po1) and not PStatus(Po2)
def PorteFerme():
	return not PStatus(Pf2)	# Pas de capteur sur la porte 1 pour l'instant
def AbriOuvert():
	return not PStatus(AO)
def AbriFerme():
	return not PStatus(AF)
def TelPark():
	return PStatus(PARK)

def ARU(msg):
	Pwrite(ALIMMOT,1)
	Pwrite(ALIMTEL,1)
	Pwrite(ALIM12,1)
	Pwrite(Po1,1)
	Pwrite(Po2,1)
	Pwrite(Pf1,1)
	Pwrite(Pf2,1)
	# On prévient du problème
	Debug('ARU '+msg)
	# TODO Attente d'une commnande de déblocage
	raise ARUExcept

def delai():
	pass
def Attend(duree,park,depl,porte):
	t=threading.Timer(duree,delai)
	t.start()
	nbpark=0
	nbpos=0
	nbporte=0
	errmax=2
	while t.is_alive():
		# Surveillance du déplacement
		if park:
			if not TelPark():
				nbpark+=1
			else: 
				nbpark=0
			if nbpark > errmax:
				ARU('Erreur Park')
		if depl:
			if not AbriFerme() and not AbriOuvert():
				nbpos+=1
			else:
				nbpos=0
			if nbpos > errmax:	
				ARU('Erreur position abri')
		# TODO Décommenter quand les capteurs portes seront cablés
		#if porte:
		#	if not PortesOuvert():
		#		nbporte+=1
		#	else:
		#		nbporte=0
		#	if nbporte > errmax:
		#		ARU('Erreur portes')
		
		# TODO Verification d'une commande ARU (AU#)
		time.sleep(0.1)
		
def FermePorte1():
	Pwrite(P11,0)
	time.sleep(DPORTES)
	Pwrite(P11,1)
	
def OuvrePorte1():
	Pwrite(P12,0)
	time.sleep(DPORTES)
	Pwrite(P12,1)

def FermePorte2():
	Pwrite(P21,0)
	time.sleep(DPORTES)
	Pwrite(P21,1)
	
def OuvrePorte2():
	Pwrite(P22,0)
	time.sleep(DPORTES)
	Pwrite(P22,1)
	
class LireCmd(socketserver.StreamRequestHandler):
    def handle(self):
        CMD=self.rfile.readline().strip()                                                                                                   
        ret=EnvoiCommande(CMD)
		if isinstance(ret, bool):
			ret=int(ret)
		ret=str(ret).encode('utf8')
        self.wfile.write(ret)
	
def CmdTelnet():
	s=socketserver.TCPServer(('', 2468), LireCmd)
	s.serve_forever()
				
def EnvoiStatus(ret):
	conn.sendall(str(int(ret)).encode('utf8'))

def EnvoiMsg(ret):
	conn.sendall(str(ret).encode('utf8'))
	
def EnvoiCommande(cmd):
	CMD=cmd[:2]
	print(CMD)
	# Exécute la commande
	if  not ARRETURG:	
		# Commande en mode automatique 
		if CMD==b'AU':	# Arret d'urgence
			return ARU()
		if CMD==b'D+':
			return OuvreDome()
		elif CMD==b"D-":
			return FermeDome()
		elif CMD==b'A+':
			StartTel()
			return AlimStatus()
		elif CMD==b'P+':
			return OuvrePortes()
		elif CMD==b'P-':
			return FermePortes()
	else:	

		# Commandes seulement en arret d'urgence
		if CMD==b'OK':
			ARRETURG=False
			return 1
		elif CMD==b'pp':
			return OuvrePorte2()
		elif CMD==b'pm':
			return FermePorte2()
		if CMD==b'dd':
			return DeplaceDomeARU()
		elif CMD==b"m+":
			return StartMot()
		elif CMD==b"m-":
			return StopMot()
		elif CMD==b'a+':
			StartTel()
			return AlimStatus()

	# Commandes en manuel et auto
	if CMD==b'C?':
		Rep=str(AbriOuvert()))
		Rep=Rep+str(AbriFerme())
		Rep=Rep+str(PortesOuvert())
		Rep=Rep+str(PorteFerme())
		Rep=Rep+str(AlimStatus())
		if TelPark:
			Rep=Rep+('p')
		else:
			Rep=Rep+('n')
		return Rep	
	elif CMD==b'A?':
		return AlimStatus()
	elif CMD==b'P?':
		return PortesOuvert()
	elif CMD==b'D?':
		return AbriOuvert()		
	elif CMD==b'p-':
		return FermePorte1()
	elif CMD==b'p+':
		return OuvrePorte1()
	elif CMD==b'A-':
		StopTel()
		return AlimStatus()

def Debug(message):
	# Affiche les informations
	print(message)
	
def OuvrePortes():
	if PortesOuvert():
		# Les portes sont déjà ouvertes
		return 0
	if not AbriFerme() and not AbriOuvert():
		# Abri non fermé, fermeture des portes impossible
		Debug("Fermeture des portes impossible: Position incorrecte de l'abri.")
		return 0
	StartMot()
	Debug('Ouverture des portes...')
	Pwrite(P12,0)
	Debug('Ouverture porte 1...')
	Attend(5,1,1,0)
	Debug('Ouverture porte 2...')
	Pwrite(P22,0)
	Attend(DPORTESCAPTEURS,1,1,0)
	while not PortesOuvert():
		Attend(0.5,1,1,0)
	Attend(5,1,1,0)
	Pwrite(P12,1)
	Pwrite(P22,1)
	Debug('Portes ouvertes')
	return 1
	
def FermePortes():
	if not PortesOuvert():
		Debug('Portes déjà fermées')
		# Les portes sont déjà fermées
		return 0
	if not AbriFerme():
		# Abri non fermé, fermeture des portes impossible
		Debug('Fermeture des portes impossible: Abri non fermé. ')
		return 0
	# TODO Voir si utile de vérifier l'état Park
	StopMot()
	Pwrite(P21,0)
	Debug('Fermeture des portes...')
	Debug('Fermeture porte 2...')
	Attend(5,1,1,0)
	Pwrite(P11,0)
	Debug('Fermeture porte 1...')
	Attend(DPORTES,1,1,0)
	Debug('Portes fermées')
	Pwrite(P11,1)
	Pwrite(P21,1)
	return 1
	
def DeplaceDomeARU():
	# /!\ Attention aucune sécurité !!!
	Debug("/!\ Déplacement manuel du dome")
	
def DeplaceDome(sens):
	global DEPLACEMENT
	EtatAbri=AbriFerme()	# Enregistre la position actuelle de l'abri
	if (not AbriFerme() and not AbriOuvert()) or (AbriFerme() and AbriOuvert()):
		# Problème de capteur
		Debug('Problème de capteur de position abri')
		return 0
	if not TelPark():
		# Télescope non parqué
		# TODO Tenter de parquer le télescope
		Debug('Télescope non parqué')
		return 0
	StopTel()
	if not PortesOuvert():
		if not MoteurStatus():
			StartMot()
		OuvrePortes()
	elif not MoteurStatus():
		StartMot()
		Attend(DMOTEUR,True, False,False)
	#OuvrePortes()
	DEPLACEMENT=True
	Debug('Demarrage moteur')
	Pwrite(MOTEUR,0)
	time.sleep(0.6)
	Pwrite(MOTEUR,1)
	Attend(DABRI/3,1,0,1)	# Déplacement de 1/3 du temps total
	if AbriOuvert() or AbriFerme():
		Debug("Relance commande moteur abri")
		# Ca n'a pas bougé, on relance la commande
		Pwrite(MOTEUR,0)
		time.sleep(0.6)
		Pwrite(MOTEUR,1)
	Attend(DABRI*2/3,1,0,1)	# On fini le déplacement (2/3 du temps total)
	while (not AbriOuvert() and not AbriFerme()):
		Attend(1,True, False, True)
	DEPLACEMENT=False
	if EtatAbri==AbriFerme():
		Debug("L'abri ne s'est pas déplacé")
		return 0
	elif AbriOuvert() or AbriFerme():
		return 1
	else:
		Debug("Position incorrecte de l'abri")
		# Abri ni ouvert, ni fermé :-(
		return 0
			
def OuvreDome():
	Debug('Ouverture dome...')
	if AbriOuvert():
		Debug('Erreur: Abri déjà ouvert')
		return 0
	if DeplaceDome(True):
		Debug('Dome ouvert')
		StartTel()
		return 1
	else:
		Debug("Problème déplacement dome")
		StopTel()
		return 0

def FermeDome():
	Debug('Fermeture dome...')
	if AbriFerme():
		Debug('Erreur: Abri déjà fermé')
		return 0
	StopTel()
	if DeplaceDome(False):
		StopMot()
		FermePortes()
		Debug('Dome fermé')
		return 1
	else:
		Debug("Problème déplacement dome")
		return 0
	
##### SETUP ######
# Initialisation des entrées/sorties
# Initialisation du port série, du socket

# Sorties

Pwrite(ALIM12,1)
Pinit(ALIM12,Constants.OUTPUT)
Pwrite(ALIMTEL,1)
Pinit(ALIMTEL,Constants.OUTPUT)
Pwrite(ALIMMOT,1)
Pinit(ALIMMOT,Constants.OUTPUT)
Pwrite(MOTEUR,1)
Pinit(MOTEUR,Constants.OUTPUT)
Pwrite(P11,1)
Pinit(P11,Constants.OUTPUT)
Pwrite(P12,1)
Pinit(P12,Constants.OUTPUT)
Pwrite(P21,1)
Pinit(P21,Constants.OUTPUT)
Pwrite(P22,1)
Pinit(P22,Constants.OUTPUT)

# Entrées 
Pinit(AO,Constants.PULLUP)
Pinit(AF,Constants.PULLUP)
Pinit(Po1,Constants.PULLUP)
Pinit(Po2,Constants.PULLUP)
Pinit(Pf1,Constants.PULLUP)
Pinit(Pf2,Constants.PULLUP)
Pinit(PARK-14,Constants.ANALOG)

TM.clearDisplay()
#TM.segments[0]="START   "

# Thread de lecture des infos en provenance du réseau
tnet=threading.Thread(target=CmdTelnet)                                                                                                     
tnet.start()                                                                                                                                

Debug('Fin setup.')
TM.segments[0]="On      "
TM.leds[0]=1

# Etat du dome initialisation des interrupteurs
if AbriOuvert():
	StartTel()
	StartMot()
##### BOUCLE PRINCIPALE #####

while True:
	# MAJEtatPark() # Interruption ?
	# /!\ TODO ne pas surveiller pendant le déplacement
	if not ARRETURG and not DEPLACEMENT and not AbriOuvert() and not AbriFerme():
		ARU("Erreur de position Abri")
	# TODO Bouton arret d'urgence'
	except KeyboardInterrupt:
		raise
	except ARUExcept:
		ARRETURG=True
		pass
		# Arret d'urgence
		# TODO A gérer, pour l'instant ne fait rien...
	time.sleep(0.5)

