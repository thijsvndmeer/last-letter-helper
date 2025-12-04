# Last-Letter Helper

Een compacte overlay die helpt bij het bekende "laatste letter"-woordspel. De tool kijkt naar de laatste letter van het vorige ingezonden woord en stelt meerdere korte suggesties voor die met die letter beginnen. De overlay blijft altijd bovenaan, kan met de muis versleept worden en werkt zowel met het meegeleverde `words_alpha.txt` bestand als met een externe systeem-woordenlijst.

## Belangrijkste functies
- **Laatste letter als input**: na het indienen van een woord wordt de laatste letter automatisch opgeslagen voor de volgende ronde.
- **Slimme suggesties**: altijd tot vijf opties die beginnen met de juiste letter, geordend van kort naar lang en zeldzame letters laag in de lijst. Reeds gebruikte woorden worden overgeslagen.
- **Live feedback**: toont wat je typt, markeert prefix- en binnenwoordmatches met kleur, en laat de volgende letter van de beste suggestie zien.
- **Waarschuwingen**: laat weten wanneer er geen geldige woorden meer zijn voor de huidige letter.
- **Rondebeheer**: houdt score en langste woord per ronde bij en herstelt de woordlijst met één toets.
- **Overlay-bediening**: blijft boven andere vensters, is versleepbaar en kan via sneltoetsen worden getoond of verborgen.

## Sneltoetsen
- **F7** – Overlay tonen of verbergen.
- **F6** – Nieuwe ronde starten (score resetten en woordlijst terugzetten).
- **F8** – Afsluiten.
- **Enter** – Huidige invoer indienen en de volgende laatste letter opslaan.
- **Backspace** – Laatste teken verwijderen.

## Uitvoeren vanaf broncode
Zorg dat Python 3 en de afhankelijkheden zijn geïnstalleerd (PyQt5 en pynput). Start daarna de overlay:

```bash
python wordbomb_typing_overlay.py
```

Het venster opent direct en begint met luisteren naar toetsenbordinvoer. Typ of plak geen cijfers of speciale tekens; die worden genegeerd om de invoer schoon te houden.
