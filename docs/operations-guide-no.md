# Driftshåndbok for Safe YouTube Viewer for Kids

## Velkommen!

Denne håndboken hjelper deg med å drifte og vedlikeholde Safe YouTube Viewer for Kids på din Hetzner VPS-server. Alt er forklart i klart norsk språk, og du trenger ikke teknisk bakgrunn for å følge disse prosedyrene.

**Mål med denne håndboken:**
- Gi deg trygghet i daglig drift av applikasjonen
- Hjelpe deg med vanlige vedlikeholdsoppgaver
- Vise deg hvordan du løser vanlige problemer
- Forberede deg på nødsituasjoner

**Viktig:** Alle kommandoer må kjøres som root-bruker på serveren din. Logg inn via SSH: `ssh root@<din-server-ip>`

---

## Innholdsfortegnelse

1. [Daglig drift](#daglig-drift)
   - [Starte og stoppe tjenesten](#starte-og-stoppe-tjenesten)
   - [Se logger](#se-logger)
   - [Bruke overvåkingsscriptene](#bruke-overvåkingsscriptene)

2. [Sikkerhetskopi og gjenoppretting](#sikkerhetskopi-og-gjenoppretting)
   - [Sikkerhetskopi (Backup)](#sikkerhetskopi-backup)
   - [Gjenoppretting (Restore)](#gjenoppretting-restore)
   - [Teste gjenoppretting](#teste-gjenoppretting)

3. [Vedlikehold](#vedlikehold)
   - [Ukentlig vedlikehold](#ukentlig-vedlikehold)
   - [Månedlig vedlikehold](#månedlig-vedlikehold)
   - [Overvåkingsverktøy](#overvåkingsverktøy)

4. [Oppdatering av applikasjonen](#oppdatering-av-applikasjonen)
   - [Kjøre oppdatering](#kjøre-oppdatering)
   - [Hva skjer under oppdatering](#hva-skjer-under-oppdatering)
   - [Automatisk tilbakestilling](#automatisk-tilbakestilling)

5. [Feilsøking](#feilsøking)
   - [Tjenesten starter ikke](#tjenesten-starter-ikke)
   - [Ingen videoer vises](#ingen-videoer-vises)
   - [Kan ikke logge inn](#kan-ikke-logge-inn)
   - [Andre vanlige problemer](#andre-vanlige-problemer)

6. [Bytte av adminpassord](#bytte-av-adminpassord)

7. [Nødprosedyrer](#nødprosedyrer)
   - [Nødkontakter](#nødkontakter)
   - [Nødsituasjoner](#nødsituasjoner)
   - [Når skal du ringe for hjelp?](#når-skal-du-ringe-for-hjelp)

---

## Daglig drift

### Starte og stoppe tjenesten

Applikasjonen kjører som en systemtjeneste som heter `youtube-viewer.service`. Her er kommandoene du trenger:

#### Starte tjenesten

```bash
sudo systemctl start youtube-viewer.service
```

**Hva gjør denne kommandoen?** Starter applikasjonen hvis den er stoppet.

#### Stoppe tjenesten

```bash
sudo systemctl stop youtube-viewer.service
```

**Hva gjør denne kommandoen?** Stopper applikasjonen. Bruk dette før du skal gjøre vedlikehold eller bytte passord.

**Viktig:** Når tjenesten stoppes, nullstilles alle admin-økter. Du må logge inn på nytt etter omstart.

#### Starte tjenesten på nytt

```bash
sudo systemctl restart youtube-viewer.service
```

**Hva gjør denne kommandoen?** Stopper og starter applikasjonen. Nyttig etter konfigurasjonendringer.

#### Sjekke tjenestens status

```bash
sudo systemctl status youtube-viewer.service
```

**Hva gjør denne kommandoen?** Viser om tjenesten kjører eller ikke.

**Slik tolker du statusen:**
- `active (running)` = **Kjører** ✅ (alt OK)
- `inactive (dead)` = **Stoppet** ⏸️ (tjenesten er stoppet)
- `failed` = **Feilet** ❌ (noe er galt, se logger)

**Eksempel på output når alt er OK:**

```
● youtube-viewer.service - Safe YouTube Viewer for Kids
   Loaded: loaded (/etc/systemd/system/youtube-viewer.service; enabled)
   Active: active (running) since Wed 2025-11-13 10:15:22 UTC; 2h 30min ago
```

---

### Se logger

Logger viser hva applikasjonen gjør og hvilke feil som eventuelt oppstår. Du bruker kommandoen `journalctl` for å se logger.

#### Vis siste 50 linjer fra loggen

```bash
journalctl -u youtube-viewer.service -n 50
```

**Hva gjør denne kommandoen?** Viser de 50 siste loggmeldingene. Nyttig for å se hva som skjedde nylig.

#### Følg nye loggmeldinger i sanntid

```bash
journalctl -u youtube-viewer.service -f
```

**Hva gjør denne kommandoen?** Viser nye loggmeldinger fortløpende. Trykk `Ctrl+C` for å avslutte.

#### Vis logger fra en bestemt dato

```bash
journalctl -u youtube-viewer.service --since "2025-11-01"
```

**Hva gjør denne kommandoen?** Viser alle logger fra 1. november 2025 og fremover.

#### Vis logger fra siste timen

```bash
journalctl -u youtube-viewer.service --since "1 hour ago"
```

**Hva gjør denne kommandoen?** Viser alle logger fra den siste timen.

#### Filtrer kun feilmeldinger

```bash
journalctl -u youtube-viewer.service | grep ERROR
```

**Hva gjør denne kommandoen?** Viser bare linjer som inneholder ordet "ERROR". Nyttig for å finne problemer raskt.

**Eksempel på loggutskrift:**

```
Nov 13 12:45:11 server uvicorn[1234]: INFO:     Application startup complete.
Nov 13 12:45:15 server uvicorn[1234]: INFO:     172.17.0.1:45678 - "GET /health HTTP/1.1" 200
Nov 13 12:50:23 server uvicorn[1234]: ERROR:    Failed to fetch video details: Video unavailable
```

---

### Bruke overvåkingsscriptene

Applikasjonen har to nyttige script for å overvåke systemet:

#### Dashboard (sanntidsoversikt)

```bash
cd /opt/youtube-viewer/app
./scripts/dashboard.sh
```

**Hva viser dette?**
- **Tjenester**: Om applikasjon og nginx kjører
- **Ressurser**: CPU, minne og diskbruk
- **I dag aktivitet**: Hvor mange videoer som er sett i dag og tid gjenstående
- **Siste feil**: Feilmeldinger fra siste timen

**Bruk dette når:** Du vil ha en rask oversikt over systemets status akkurat nå.

**Eksempel på dashboard-output:**

```
═══════════════════════════════════════════════════════
  YOUTUBE VIEWER - SYSTEM DASHBOARD
═══════════════════════════════════════════════════════

📊 TJENESTER
  ✅ Applikasjon: Kjører
  ✅ Nginx: Kjører

💾 RESSURSER
  CPU: 12%
  Minne: 245MB / 2048MB (12%)
  Disk: 2.3GB / 20GB (12%)

📺 I DAG AKTIVITET (2025-11-13)
  Videoer sett: 8
  Total tid: 24 minutter
  Tid gjenstående: 6 minutter (av 30 minutters grense)

⚠️ SISTE FEIL (siste time)
  Ingen feil funnet
```

#### Helsekontroll (detaljert ukentlig sjekk)

```bash
cd /opt/youtube-viewer/app
./scripts/check-health.sh
```

**Hva viser dette?**
- **Tjeneste Status**: Om applikasjon og nginx kjører
- **Diskplass**: Hvor mye diskplass som er brukt
- **Siste Feil**: Feilmeldinger fra siste 24 timer
- **Database Status**: Databasestørrelse og integritet
- **Backup Status**: Når siste backup ble tatt

**Bruk dette når:** Du skal gjøre ukentlig vedlikehold eller undersøke et problem grundig.

**Eksempel på helsekontroll-output:**

```
═══════════════════════════════════════════════════════
  YOUTUBE VIEWER - HELSEKONTROLL
═══════════════════════════════════════════════════════

✅ TJENESTE STATUS
  ✓ Applikasjon: Kjører
  ✓ Nginx: Kjører

✅ DISKPLASS
  ✓ Diskplass: 12% brukt (OK)
    Brukt: 2.3GB
    Tilgjengelig: 17.7GB
    Monteringspunkt: /opt/youtube-viewer

✅ SISTE FEIL (siste 24 timer)
  ✓ Ingen feil funnet

✅ DATABASE STATUS
  ✓ Database størrelse: 4.2MB
  ✓ Integritet: OK

✅ BACKUP STATUS
  ✓ Siste backup: app-20251113-020015.db
    Størrelse: 4.2MB
    Alder: 10 timer siden
  ✓ Totalt 7 backups funnet
```

---

## Sikkerhetskopi og gjenoppretting

### Sikkerhetskopi (Backup)

Systemet tar automatisk sikkerhetskopi av databasen hver natt kl. 02:00 UTC. Sikkerhetskopiene lagres i 7 dager før de automatisk slettes.

#### Se liste over sikkerhetskopier

```bash
ls -lht /opt/youtube-viewer/backups/
```

**Hva gjør denne kommandoen?** Viser alle sikkerhetskopier, nyeste først.

**Filnavnformat:** `app-YYYYMMDD-HHMMSS.db`
- Eksempel: `app-20251113-020015.db` = 13. november 2025, kl. 02:00:15

#### Ta manuell sikkerhetskopi

```bash
cd /opt/youtube-viewer/app
./scripts/backup.sh
```

**Hva gjør dette scriptet?**
1. Kjører en kontrollpunkt på databasen (sikrer at alt er lagret)
2. Kopierer databasen til en ny fil med tidsstempel
3. Setter riktige rettigheter på sikkerhetskopien
4. Sletter sikkerhetskopier eldre enn 7 dager

**Når bør du ta manuell backup?**
- Før du kjører en oppdatering
- Før du bytter passord
- Før du gjør andre større endringer

**Hvor lagres backupene?** `/opt/youtube-viewer/backups/`

**Oppbevaringstid:** 7 dager (automatisk rydding)

---

### Gjenoppretting (Restore)

Hvis noe går galt, kan du gjenopprette databasen fra en sikkerhetskopi.

#### Se tilgjengelige sikkerhetskopier

```bash
ls -1t /opt/youtube-viewer/backups/app-*.db | head -7
```

**Hva gjør denne kommandoen?** Viser de 7 nyeste sikkerhetskopiene.

#### Gjenopprett fra sikkerhetskopi

```bash
cd /opt/youtube-viewer/app
sudo ./scripts/restore.sh app-20251113-020015.db
```

**Viktig:** Bytt `app-20251113-020015.db` med navnet på den sikkerhetskopien du vil gjenopprette fra.

**Hva skjer under gjenoppretting?**

1. **Tjenesten stoppes automatisk** (youtube-viewer.service)
2. **Nåværende database sikkerhetskoperes** (lagres som `app.db.before-restore`)
3. **Sikkerhetskopien kopieres** til aktiv database (`app.db`)
4. **Rettigheter settes** (chmod 600, owner youtube-viewer:youtube-viewer)
5. **Integritetskontroll kjøres** (`PRAGMA integrity_check` må returnere "ok")
6. **Automatisk tilbakestilling** hvis integritet feiler (gjenoppretter `app.db.before-restore`)
7. **Tjenesten startes på nytt**
8. **Helsekontroll verifiserer** at alt fungerer (HTTP health endpoint)

**Eksempel på vellykket gjenoppretting:**

```
Stopping youtube-viewer.service...
Creating safety backup: app.db.before-restore
Restoring backup: app-20251113-020015.db
Setting permissions...
Running integrity check...
Database integrity: OK ✓
Starting youtube-viewer.service...
Verifying health endpoint...
Health check: OK ✓

Restore completed successfully!
```

**Hvis noe går galt:**

Restore-scriptet vil automatisk rulle tilbake til `app.db.before-restore` hvis integritetskontrollen feiler. Du vil da se:

```
ERROR: Database integrity check failed!
Rolling back to previous database...
Restore failed. Previous database has been restored.
```

I dette tilfellet: Prøv en eldre sikkerhetskopi.

---

### Teste gjenoppretting

Det er viktig å teste at gjenopprettingsprosedyren fungerer. Gjør dette månedlig.

#### Slik tester du restore-funksjonen:

1. **Ta en manuell backup først** (slik at du har en fersk backup å gå tilbake til)

```bash
cd /opt/youtube-viewer/app
./scripts/backup.sh
```

2. **Gjør en liten endring** i admin-grensesnittet (f.eks. endre daglig grense)

3. **Gjenopprett fra en eldre backup** (2-3 dager gammel)

```bash
sudo ./scripts/restore.sh <backup-filnavn>
```

4. **Verifiser at endringen du gjorde er borte** (daglig grense tilbake til gammel verdi)

5. **Gjenopprett produksjonsdatabasen** fra den ferskebackupen du tok i steg 1

```bash
sudo ./scripts/restore.sh <fersk-backup-filnavn>
```

6. **Verifiser at alt er tilbake til normalt**

**Dette bekrefter:** Restore-funksjonen fungerer, og du kan stole på sikkerhetskopiene dine i en nødsituasjon.

---

## Vedlikehold

### Ukentlig vedlikehold

Sett av 10 minutter hver uke til å kjøre denne sjekklisten. Dette hjelper deg med å oppdage problemer tidlig.

#### ☐ 1. Kjør helsekontroll

```bash
cd /opt/youtube-viewer/app
./scripts/check-health.sh
```

**Hva skal du se etter:**
- Alle sjekker viser ✅ eller ✓ (grønn hake)
- Ingen røde ❌ eller advarsler ⚠️

**Hvis du ser advarsler:**
- **Diskplass >80%**: Se [Lav diskplass](#lav-diskplass)
- **Tjeneste stoppet**: Se [Tjenesten starter ikke](#tjenesten-starter-ikke)
- **Database integritet feilet**: Gjenopprett fra backup umiddelbart
- **Siste backup >48 timer**: Sjekk at backup-timeren kjører (se nedenfor)

#### ☐ 2. Verifiser at sikkerhetskopier finnes

```bash
ls -lht /opt/youtube-viewer/backups/ | head -8
```

**Hva skal du se etter:**
- Minst 7 sikkerhetskopier er listet
- Nyeste sikkerhetskopi er mindre enn 48 timer gammel
- Filstørrelsene er fornuftige (minst noen MB)

**Hvis nyeste backup er >48 timer:**

Sjekk status på backup-timeren:

```bash
systemctl list-timers | grep youtube-viewer-backup
```

Hvis timeren ikke vises eller er "n/a", må du kanskje aktivere den på nytt. Kontakt teknisk support.

#### ☐ 3. Sjekk diskplass

```bash
df -h /opt/youtube-viewer
```

**Hva skal du se etter:**
- Mindre enn 80% brukt (mer enn 20% ledig)

**Eksempel på output:**

```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        20G  2.3G  17.7G  12% /opt/youtube-viewer
```

I dette eksemplet: **12% brukt = OK** ✅

Hvis diskplass er >80%, se [Lav diskplass](#lav-diskplass).

#### ☐ 4. Se gjennom feillogger

```bash
journalctl -u youtube-viewer.service --since "7 days ago" | grep ERROR
```

**Hva skal du se etter:**
- Ingen gjentatte feilmeldinger
- Ingen uventede feil

**Vanlige feil du kan ignorere:**
- Enkelttilfeller av "Video unavailable" (YouTube fjernet video)
- Sporadiske nettverksfeil

**Feil du bør undersøke:**
- Gjentatte feil (samme feilmelding mange ganger)
- Database-feil
- API-feil (YouTube API key problemer)
- Se [Feilsøking](#feilsøking) for hjelp

---

### Månedlig vedlikehold

Sett av 30 minutter hver måned til å kjøre denne sjekklisten. Dette sikrer langsiktig stabilitet.

#### ☐ 1. Verifiser SSL-sertifikat

```bash
sudo certbot certificates
```

**Hva skal du se etter:**
- Sertifikatet utløper mer enn 30 dager frem i tid
- "VALID" status

**Eksempel på output:**

```
Certificate Name: ditt-domene.no
  Domains: ditt-domene.no
  Expiry Date: 2026-02-10 12:34:56+00:00 (VALID: 89 days)
```

I dette eksemplet: **89 dager til utløp = OK** ✅

**Hvis sertifikatet utløper om <30 dager:**

Certbot skal automatisk fornye sertifikatet. Hvis det ikke har skjedd:

```bash
sudo certbot renew
```

#### ☐ 2. Kjør restore-test

Se [Teste gjenoppretting](#teste-gjenoppretting) for detaljert prosedyre.

**Hvorfor er dette viktig?**
- Bekrefter at sikkerhetskopiene dine faktisk fungerer
- Øver på restore-prosedyren før du trenger den i en nødsituasjon
- Gir deg trygghet

#### ☐ 3. Oppdater system

```bash
sudo apt update && sudo apt upgrade -y
```

**Hva gjør denne kommandoen?**
1. `apt update`: Henter informasjon om nye oppdateringer
2. `apt upgrade -y`: Installerer alle sikkerhetoppdateringer (-y = svar ja automatisk)

**Eksempel på output:**

```
Reading package lists... Done
Building dependency tree... Done
The following packages will be upgraded:
  libssl3 openssl
2 upgraded, 0 newly installed, 0 to remove
```

**Viktig:** Hvis kjernen (kernel) oppdateres, må du starte serveren på nytt:

```bash
sudo reboot
```

Serveren vil være utilgjengelig i 1-2 minutter mens den starter på nytt.

---

### Overvåkingsverktøy

Du har to script tilgjengelig for overvåking:

#### check-health.sh - Ukentlig helsekontroll

**Bruk til:** Ukentlig vedlikehold og grundig problemundersøkelse

**Hva det sjekker:**
- ✅ **Tjeneste Status**: Om applikasjon og nginx kjører
- ✅ **Diskplass**: Brukt/tilgjengelig diskplass med advarsel ved >80%
- ✅ **Siste Feil**: Feilmeldinger fra siste 24 timer
- ✅ **Database Status**: Størrelse og integritet (PRAGMA quick_check)
- ✅ **Backup Status**: Siste backup, alder, totalt antall backups

**Hvor kjøre:**

```bash
cd /opt/youtube-viewer/app
./scripts/check-health.sh
```

**Alert-terskler:**
- 🔴 **Kritisk**: Tjeneste nede, database integritet feilet
- ⚠️ **Advarsel**: Diskplass >80%, siste backup >48 timer, feilmeldinger funnet

#### dashboard.sh - Sanntidsoversikt

**Bruk til:** Rask daglig sjekk, sanntidsovervåking under problemer

**Hva det viser:**
- 📊 **Tjenester**: Sanntidsstatus for applikasjon og nginx
- 💾 **Ressurser**: CPU, minne og diskbruk
- 📺 **I dag aktivitet**: Videoer sett, total tid, tid gjenstående
- ⚠️ **Siste feil**: Feilmeldinger fra siste timen

**Hvor kjøre:**

```bash
cd /opt/youtube-viewer/app
./scripts/dashboard.sh
```

**Tips:** Kjør dashboard.sh når du vil ha en rask oversikt. Kjør check-health.sh for grundig ukentlig kontroll.

---

## Oppdatering av applikasjonen

### Kjøre oppdatering

Når det kommer nye versjoner av applikasjonen, bruker du deploy-scriptet for å oppdatere.

**Viktig:** Ta alltid en manuell backup før oppdatering!

#### Steg 1: Ta backup

```bash
cd /opt/youtube-viewer/app
./scripts/backup.sh
```

#### Steg 2: Kjør oppdatering

```bash
cd /opt/youtube-viewer/app
./scripts/deploy.sh
```

**Hvor lang tid tar det?** 2-5 minutter avhengig av størrelsen på oppdateringen.

**Eksempel på vellykket oppdatering:**

```
=== DEPLOYMENT STARTED ===
Validating environment...                  ✓
Pulling latest code...                     ✓
Running database migrations...             ✓
Installing backend dependencies...         ✓
Running backend quality checks...          ✓
Running TIER 1 safety tests...             ✓
Building frontend...                       ✓
Running frontend tests...                  ✓
Restarting service...                      ✓
Verifying health endpoint...               ✓

=== DEPLOYMENT SUCCESSFUL ===
```

---

### Hva skjer under oppdatering

Oppdateringsprosessen har 14 steg:

1. **Validerer miljøvariabler** (DATABASE_PATH, YOUTUBE_API_KEY)
2. **Henter ny kode** fra GitHub (`git pull origin main`)
3. **Kjører database-migrasjoner** (hvis nødvendig)
4. **Installerer backend-avhengigheter** (`uv sync`)
5. **Kjører backend kvalitetskontroller** (formattering, linting, typesjekk)
6. **Kjører TIER 1 sikkerhetstester** (KRITISK - stopper hvis tester feiler)
7. **Verifiserer backend test-dekning** (85% mål)
8. **Verifiserer ingen async/await** (arkitekturkrav)
9. **Bygger frontend** (`npm install`, `npm run build`)
10. **Kjører frontend kvalitetskontroller** (ESLint, Prettier)
11. **Kjører frontend-tester** (`npm test`)
12. **Kjører database checkpoint** (sikrer all data er lagret)
13. **Starter tjenesten på nytt** (`systemctl restart`)
14. **Verifiserer helsestatus** (HTTP health endpoint)

**Viktig:** Hvis NOEN av disse stegene feiler, vil oppdateringen stoppe og rulle tilbake automatisk.

---

### Automatisk tilbakestilling

Hvis oppdateringen feiler på noe punkt, skjer dette automatisk:

1. **Gjenoppretter forrige kode-versjon** (`git reset --hard`)
2. **Bygger frontend på nytt** med gammel kode
3. **Starter tjenesten på nytt**
4. **Verifiserer helse** (sikrer at gammel versjon kjører igjen)

**Du vil se:**

```
ERROR: Deployment failed at step: Running TIER 1 safety tests
Rolling back to previous version...
Restoring previous code...                ✓
Rebuilding frontend...                    ✓
Restarting service...                     ✓
Verifying health...                       ✓

=== ROLLBACK SUCCESSFUL ===
Previous version has been restored.
```

**Dette betyr:** Applikasjonen kjører igjen med gammel versjon. Ingen data er tapt.

**Hva skal du gjøre?**
1. Se deployment-loggen for detaljer: `tail -100 /opt/youtube-viewer/logs/deployments.log`
2. Kontakt teknisk support med feilmeldingen

---

## Feilsøking

### Tjenesten starter ikke

**Symptom:** `systemctl status youtube-viewer.service` viser `failed` eller `inactive (dead)`

#### Steg 1: Sjekk status og logger

```bash
sudo systemctl status youtube-viewer.service
journalctl -u youtube-viewer.service -n 50
```

**Se etter feilmeldinger** i loggene. Vanlige årsaker:

#### Årsak 1: Database-tillatelser feil

**Feilmelding i logger:** "Permission denied" eller "unable to open database file"

**Løsning:**

```bash
cd /opt/youtube-viewer/app
sudo chown youtube-viewer:youtube-viewer data/app.db
sudo chmod 600 data/app.db
sudo systemctl start youtube-viewer.service
```

#### Årsak 2: Miljøvariabler mangler

**Feilmelding i logger:** "DATABASE_PATH not set" eller "YOUTUBE_API_KEY not set"

**Løsning:**

```bash
cd /opt/youtube-viewer/app
cat .env
```

Sjekk at `.env` filen inneholder:
```
DATABASE_PATH=./data/app.db
YOUTUBE_API_KEY=<din-nøkkel>
```

Hvis noe mangler, rediger `.env` filen og start på nytt:

```bash
sudo systemctl start youtube-viewer.service
```

#### Årsak 3: Port 8000 allerede i bruk

**Feilmelding i logger:** "Address already in use" eller "error binding to 0.0.0.0:8000"

**Løsning:**

Finn prosessen som bruker port 8000:

```bash
sudo lsof -i :8000
```

Drep prosessen (bytt `<PID>` med prosess-ID fra output over):

```bash
sudo kill <PID>
sudo systemctl start youtube-viewer.service
```

#### Årsak 4: Database korrupt

**Feilmelding i logger:** "database disk image is malformed" eller "file is not a database"

**Løsning:**

Gjenopprett fra backup (se [Gjenoppretting](#gjenoppretting-restore)):

```bash
cd /opt/youtube-viewer/app
sudo ./scripts/restore.sh <siste-backup-filnavn>
```

---

### Ingen videoer vises

**Symptom:** Barneskjermen er tom, eller viser meldingen "Ingen videoer tilgjengelig"

#### Årsak 1: Ingen kanaler lagt til ennå

**Løsning:**

1. Logg inn på admin-grensesnittet
2. Gå til "Kanaler"
3. Legg til minst én YouTube-kanal eller spilleliste
4. Vent noen sekunder mens videoer lastes ned

#### Årsak 2: YouTube API-nøkkel ugyldig

**Sjekk loggene for API-feil:**

```bash
journalctl -u youtube-viewer.service -n 100 | grep "API"
```

**Feilmeldinger du kan se:**
- "The request cannot be completed because you have exceeded your quota"
- "API key not valid"
- "API key expired"

**Løsning:**

1. Sjekk at YouTube API-nøkkelen er riktig i `.env` filen
2. Sjekk API-kvoten i Google Cloud Console
3. Hvis kvoten er brukt opp: Vent til neste dag (kvote nullstilles ved midnatt Pacific Time)

#### Årsak 3: Nettverksproblemer

**Sjekk om serveren har internett-tilgang:**

```bash
ping -c 3 www.youtube.com
```

Hvis ingen respons, sjekk nettverksinnstillinger på Hetzner.

---

### Kan ikke logge inn

**Symptom:** Admin-påloggingen viser "Feil brukernavn eller passord" selv om passordet er riktig

#### Årsak 1: Feil passord

**Løsning:** Prøv passordet nøye igjen. Sjekk Caps Lock.

#### Årsak 2: Økter nullstilt etter omstart

**Husk:** Når tjenesten startes på nytt, nullstilles alle økter. Du må logge inn på nytt.

**Løsning:** Logger inn igjen med ditt passord.

#### Årsak 3: Glemt passord

**Løsning:** Se [Bytte av adminpassord](#bytte-av-adminpassord).

#### Årsak 4: Database-problem påvirker innstillinger-tabellen

**Sjekk database-integritet:**

```bash
cd /opt/youtube-viewer/app
./scripts/check-health.sh
```

Hvis database-integritet feiler, gjenopprett fra backup.

---

### Andre vanlige problemer

#### Backup feiler

**Symptom:** `./scripts/backup.sh` feiler med feilmelding

**Mulige årsaker:**
- Diskplass full (se [Lav diskplass](#lav-diskplass))
- Database-tillatelser feil (samme løsning som [Tjenesten starter ikke - Årsak 1](#årsak-1-database-tillatelser-feil))
- Database låst (applikasjonen må kjøre for at WAL checkpoint skal fungere)

**Løsning:**

```bash
# Sjekk diskplass først
df -h /opt/youtube-viewer

# Sjekk at tjenesten kjører
sudo systemctl status youtube-viewer.service

# Prøv backup igjen
cd /opt/youtube-viewer/app
./scripts/backup.sh
```

#### Lav diskplass

**Symptom:** `df -h` viser >80% brukt, eller `check-health.sh` viser advarsel

**Løsning 1: Slett gamle backups**

```bash
# List backups sortert etter alder
ls -lht /opt/youtube-viewer/backups/

# Slett backups eldre enn 3 dager (kun i nødsituasjon!)
find /opt/youtube-viewer/backups/ -name "app-*.db" -mtime +3 -delete
```

**Løsning 2: Rensk logger**

```bash
# Slett logger eldre enn 3 dager
sudo journalctl --vacuum-time=3d
```

**Løsning 3: Sjekk deployment-logger**

```bash
# Se størrelsen på deployment-logger
du -sh /opt/youtube-viewer/logs/

# Hvis de er store, kan du slette gamle deployment-logger (valgfritt)
sudo truncate -s 0 /opt/youtube-viewer/logs/deployments.log
```

#### Database-feil

**Symptom:** Feilmeldinger om database i loggene, eller data vises feil i applikasjonen

**Løsning:**

1. **Kjør integritetssjekk:**

```bash
cd /opt/youtube-viewer/app
./scripts/check-health.sh
```

2. **Hvis integritet feiler, gjenopprett fra backup:**

```bash
sudo ./scripts/restore.sh <siste-backup-filnavn>
```

3. **Verifiser at alt fungerer etter restore:**

```bash
./scripts/check-health.sh
```

#### Deployment feiler

**Symptom:** `./scripts/deploy.sh` feiler og ruller tilbake

**Hva skjer:** Automatisk rollback gjenoppretter forrige versjon (se [Automatisk tilbakestilling](#automatisk-tilbakestilling))

**Hva skal du gjøre:**

1. **Se deployment-loggen:**

```bash
tail -100 /opt/youtube-viewer/logs/deployments.log
```

2. **Kontakt teknisk support** med feilmeldingen fra loggen

3. **Applikasjonen kjører fortsatt** med gammel versjon - ingen hastverk

---

## Bytte av adminpassord

Hvis du har glemt adminpassordet eller vil bytte det, følg disse stegene:

#### Steg 1: Stopp tjenesten

```bash
sudo systemctl stop youtube-viewer.service
```

**Viktig:** Tjenesten MÅ stoppes før du bytter passord.

#### Steg 2: Bytt passord

```bash
cd /opt/youtube-viewer/app
uv run python backend/db/init_db.py <nytt_passord>
```

**Viktig:** Bytt `<nytt_passord>` med ditt valgte passord.

**Eksempel:**

```bash
uv run python backend/db/init_db.py MittSikre123Passord
```

**Hva skjer:** Passordet blir automatisk kryptert med bcrypt (sikkerhetshashing) før det lagres i databasen.

#### Steg 3: Start tjenesten

```bash
sudo systemctl start youtube-viewer.service
```

#### Steg 4: Logg inn med nytt passord

1. Åpne admin-grensesnittet i nettleseren
2. Logg inn med ditt nye passord

**Husk:** Økter nullstilles ved omstart - du må logge inn på nytt.

---

## Nødprosedyrer

### Nødkontakter

Fyll inn kontaktinformasjon i feltene nedenfor. Skriv ned telefonnumre og e-postadresser du kan kontakte i en nødsituasjon.

#### Teknisk support

- **Navn:** [Fyll inn]
- **E-post:** [Fyll inn]
- **Telefon:** [Fyll inn]
- **Tilgjengelighet:** [Fyll inn, f.eks. "Hverdager 09:00-17:00"]

#### Hetzner support

- **Support-portal:** https://console.hetzner.cloud/support
- **E-post:** support@hetzner.com
- **Telefon:** +49 9831 5050 (Tyskland)
- **Dokumentasjon:** https://docs.hetzner.com/

#### Nødkontakt

- **Navn:** [Fyll inn - en annen person som kan hjelpe]
- **Telefon:** [Fyll inn]

**Viktig:** Fyll inn kontaktinformasjon i feltene merket [Fyll inn]. Skriv dette ned eller skriv ut denne håndboken med utfylt informasjon.

---

### Nødsituasjoner

#### System helt nede

**Symptom:** Applikasjonen er utilgjengelig, nettstedet laster ikke

**Umiddelbare tiltak:**

1. **Sjekk Hetzner server-status**

Logg inn på Hetzner Cloud Console: https://console.hetzner.cloud/

Sjekk at serveren kjører (grønn status). Hvis serveren er rød (stopped):
- Klikk på serveren
- Klikk "Power on"

2. **Verifiser SSH-tilgang**

```bash
ssh root@<din-server-ip>
```

Hvis SSH ikke fungerer: Serveren kan være helt nede. Bruk Hetzner Console for å starte serveren.

3. **Sjekk tjenestestatus**

```bash
sudo systemctl status youtube-viewer.service
```

Hvis tjenesten er stoppet eller feilet, prøv å starte den:

```bash
sudo systemctl start youtube-viewer.service
```

4. **Sjekk loggene for årsak**

```bash
journalctl -u youtube-viewer.service -n 50
```

5. **Hvis server er nede og du ikke kan fikse det:** Kontakt Hetzner support umiddelbart.

---

#### Database korrupt

**Symptom:** Feilmeldinger om database i loggene, applikasjonen oppfører seg rart eller krasjer

**Umiddelbare tiltak:**

1. **Stopp tjeneste umiddelbart**

```bash
sudo systemctl stop youtube-viewer.service
```

**Viktig:** IKKE fortsett å kjøre applikasjonen med korrupt database - dette kan forverre problemet.

2. **Gjenopprett fra siste backup**

```bash
cd /opt/youtube-viewer/app

# Se tilgjengelige backups
ls -1t /opt/youtube-viewer/backups/app-*.db | head -7

# Gjenopprett fra nyeste backup
sudo ./scripts/restore.sh <nyeste-backup-filnavn>
```

3. **Verifiser integritet etter gjenoppretting**

```bash
./scripts/check-health.sh
```

Sjekk at "Database Status" viser ✅ "Integritet: OK".

4. **Test at applikasjonen fungerer**

Logg inn på admin-grensesnittet og verifiser at data ser riktig ut.

5. **Hvis gjenoppretting feiler:** Prøv en eldre backup. Hvis alle backups feiler, kontakt teknisk support umiddelbart.

---

#### Sikkerhetshendelse

**Symptom:** Uventet aktivitet, mistenkelige loggmeldinger, uautorisert tilgang

**Umiddelbare tiltak:**

1. **Stopp tjeneste umiddelbart**

```bash
sudo systemctl stop youtube-viewer.service
```

2. **Se gjennom logger for mistenkelig aktivitet**

```bash
journalctl -u youtube-viewer.service -n 200
```

Se etter:
- Uventede påloggingsforsøk
- Uventede API-kall
- Feilmeldinger om autorisasjon
- Ukjente IP-adresser

3. **Lagre logger for analyse**

```bash
journalctl -u youtube-viewer.service --since "24 hours ago" > /tmp/security-incident.log
```

4. **Kontakt teknisk support umiddelbart**

Send med:
- Beskrivelse av hva du oppdaget
- Tidspunkt for hendelsen
- Loggfilen `/tmp/security-incident.log`

5. **IKKE start tjeneste før sikkerhetsproblem er løst**

Vent på instruksjoner fra teknisk support.

---

#### Disk full (Diskplass helt full)

**Symptom:** Applikasjonen feiler, backup feiler, feilmeldinger om "No space left on device"

**Umiddelbare tiltak:**

1. **Sjekk diskbruk**

```bash
df -h
```

Hvis "Use%" er 100% eller nær 100%, må du frigjøre plass umiddelbart.

2. **Slett gamle backups (kun i nødsituasjon!)**

```bash
# Slett backups eldre enn 3 dager
find /opt/youtube-viewer/backups/ -name "app-*.db" -mtime +3 -delete
```

**Advarsel:** Dette reduserer backup-historikken din. Gjør dette kun i nødsituasjon.

3. **Slett gamle logger**

```bash
# Slett logger eldre enn 3 dager
sudo journalctl --vacuum-time=3d
```

4. **Sjekk diskplass igjen**

```bash
df -h
```

Du trenger minst 20% ledig plass for at applikasjonen skal kjøre stabilt.

5. **Start tjeneste igjen etter rydding**

```bash
sudo systemctl start youtube-viewer.service
```

6. **Hvis problemet fortsetter:** Du må kanskje oppgradere til en større disk på Hetzner. Kontakt teknisk support.

---

### Når skal du ringe for hjelp?

Ring eller send e-post til teknisk support i disse situasjonene:

#### 🔴 Umiddelbart (innen 1 time)

- Tjenesten vil ikke starte etter flere forsøk
- Database gjenoppretting feiler gjentatte ganger
- Sikkerhetsvarsler eller uvanlig aktivitet
- Server helt nede og du ikke kan starte den via Hetzner Console
- Database korrupt og alle backups feiler

#### ⚠️ Snart (innen 24 timer)

- Disk full situasjon ikke løst av rydding
- Deployment feiler gjentatte ganger
- Backup-timer fungerer ikke (ingen nye backups på 48 timer)
- SSL-sertifikat utløper om <7 dager og auto-renewal feiler
- Gjentatte feil i loggene du ikke forstår

#### 📝 Når det passer (innen 1 uke)

- Spørsmål om hvordan noe fungerer
- Ønsker om nye funksjoner eller endringer
- Generell veiledning eller opplæring
- Forbedringer av ytelse eller sikkerhet

#### 💡 Du er usikker på hva som er galt

**Ingen dumme spørsmål!** Hvis du er usikker, er det alltid bedre å spørre enn å gjette.

**Før du ringer:**
1. Kjør `./scripts/check-health.sh` og noter ned advarsler
2. Sjekk `journalctl -u youtube-viewer.service -n 50` for feilmeldinger
3. Noter ned hva som skjedde like før problemet oppsto

**Informasjon som er nyttig å ha klar:**
- Hva prøvde du å gjøre?
- Hva forventet du skulle skje?
- Hva skjedde faktisk?
- Har du gjort noen endringer nylig?

---

## Vedlegg: Nyttige kommandoer

Her er en samlet liste over de mest brukte kommandoene:

### Tjenestestyring

```bash
# Sjekk status
sudo systemctl status youtube-viewer.service

# Start tjeneste
sudo systemctl start youtube-viewer.service

# Stopp tjeneste
sudo systemctl stop youtube-viewer.service

# Start tjeneste på nytt
sudo systemctl restart youtube-viewer.service
```

### Logger

```bash
# Siste 50 linjer
journalctl -u youtube-viewer.service -n 50

# Følg live
journalctl -u youtube-viewer.service -f

# Kun feil
journalctl -u youtube-viewer.service | grep ERROR

# Siste timen
journalctl -u youtube-viewer.service --since "1 hour ago"
```

### Overvåking

```bash
# Rask oversikt
cd /opt/youtube-viewer/app && ./scripts/dashboard.sh

# Detaljert helsekontroll
cd /opt/youtube-viewer/app && ./scripts/check-health.sh

# Diskplass
df -h /opt/youtube-viewer
```

### Backup og Restore

```bash
# List backups
ls -lht /opt/youtube-viewer/backups/

# Ta backup
cd /opt/youtube-viewer/app && ./scripts/backup.sh

# Gjenopprett fra backup
cd /opt/youtube-viewer/app && sudo ./scripts/restore.sh <backup-filnavn>
```

### Oppdatering

```bash
# Kjør oppdatering
cd /opt/youtube-viewer/app && ./scripts/deploy.sh

# Se deployment-logg
tail -100 /opt/youtube-viewer/logs/deployments.log
```

### Passordbytte

```bash
# Bytt adminpassord
sudo systemctl stop youtube-viewer.service
cd /opt/youtube-viewer/app
uv run python backend/db/init_db.py <nytt_passord>
sudo systemctl start youtube-viewer.service
```

---

## Avslutning

Denne håndboken skal gi deg trygghet i driften av Safe YouTube Viewer for Kids. Husk:

- **Ukentlig:** Kjør helsekontroll (10 minutter)
- **Månedlig:** Kjør full vedlikeholdssjekkliste (30 minutter)
- **Før oppdatering:** Ta alltid backup først
- **Ved problemer:** Sjekk logger og følg feilsøkingsveiledningen
- **Ved tvil:** Ring teknisk support - ingen dumme spørsmål!

**Lykke til med driften!** 🚀
