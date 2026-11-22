# order.md — Bot d'alerte de disponibilité de la PS5 Édition numérique Slim (PlayStation France → Telegram)

> **Document autonome (version 4).** Il résume toute la discussion préparatoire entre l'utilisateur et un assistant, pour qu'une IA agent (GitHub Copilot en mode agent, prévu) ou un humain puisse tout construire sans avoir assisté aux échanges. Les décisions de la section 3 sont **fermes**. Les points marqués ⚠️ sont **non vérifiés** : à tester avant de coder dessus.

---

## 1. Résumé

1. Un script Python vérifie toutes les ~5 minutes la **page produit** de la *Console PlayStation 5 Édition numérique (modèle Slim), 499,99 €* sur playstation.com/fr-fr.
2. Il lit le champ structuré de disponibilité de la page (`availability` + `type` du bouton d'achat) et détermine un statut : `DISPONIBLE`, `INDISPONIBLE` ou `INCONNU`.
3. Quand le produit passe de `INDISPONIBLE` à `DISPONIBLE` (ou `INCONNU`), il envoie un message Telegram avec les infos et un bouton cliquable ; tant qu'il reste disponible, il envoie un rappel toutes les 30 minutes.
4. Il tourne gratuitement sur **GitHub Actions** (dépôt **public**), sans dépendre du PC de l'utilisateur.
5. Il **notifie seulement** : aucun achat automatique, aucune IA dans l'exécution. L'architecture permet d'ajouter facilement d'autres produits plus tard (liste en fichier de configuration).

## 2. Profil de l'utilisateur et façon de travailler

- Étudiant français en classe préparatoire scientifique (MP) ; à l'aise en Python et en maths ; **débutant** en scraping, JSON web, API Telegram, GitHub Actions. Il ne sait pas répondre aux choix très techniques : **l'IA décide** et justifie brièvement.
- Il veut des réponses courtes, claires, en français, et un projet simple à déboguer.
- Il compte donner ce fichier à un agent de code (Copilot en mode agent) qui crée tout dans un dépôt. Il utilise aussi Perplexity pour poser des questions et déboguer.
- Il veut recevoir l'information le plus vite possible pour **acheter lui-même** : les PS5 sont rarement en stock en ce moment.
- Il veut un dépôt public mais **sûr** (aucun secret exposé).

## 3. Décisions fermes

| # | Sujet | Décision |
|---|---|---|
| 1 | Produit surveillé | **Uniquement** la console PS5 Édition numérique, modèle Slim (sans lecteur), 499,99 € |
| 2 | Source | Sa page produit (voir §4). Une requête = une page |
| 3 | Source du statut | Champs structurés `availability` (JSON-LD) et `type` du bouton d'achat ; le texte visible sert de secours/confirmation |
| 4 | Extensibilité | Liste de produits dans un fichier de configuration (JSON ou YAML) : nom, URL, SKU. Aujourd'hui **un seul** produit ; en ajouter plus tard ne doit demander aucune modification du code. Chaque produit = une page visitée, avec une pause aléatoire de quelques secondes entre deux pages |
| 5 | Déclencheur | Alerte au passage `INDISPONIBLE → DISPONIBLE` |
| 6 | Rappel | Toutes les **30 minutes** tant que le produit reste disponible (valeur en config) |
| 7 | Cas « inconnu » | **Notifié** aussi, avec la mention « statut inconnu, vérifie la page » |
| 8 | Premier lancement | Même logique que les suivants, sans traitement spécial : seul le statut courant compte |
| 9 | État sauvegardé | Table `produit → statut courant` + date du dernier message envoyé. Pas d'historique |
| 10 | Fréquence | Toutes les 5 minutes (minimum de GitHub Actions) + **jitter** aléatoire. Retards d'exécution acceptés |
| 11 | Hébergement | GitHub Actions, dépôt **public** (minutes gratuites illimitées) |
| 12 | Coût | 100 % gratuit |
| 13 | Python | 3.14 (vérifier la compatibilité des bibliothèques), code **synchrone**, `requests` + parsing HTML/JSON de la bibliothèque standard (et `beautifulsoup4` si utile) |
| 14 | Telegram | Chat privé avec un bot @BotFather ; envoi via l'API HTTP avec `requests` ; pas de commandes ; pas d'alerte de panne (erreurs dans les logs seulement) |
| 15 | Message | Titre, prix, lien, image, SKU, statut, date/heure + bouton cliquable « Acheter » |
| 16 | Robustesse | **Programmation défensive** : le programme ne doit jamais s'arrêter sur une erreur |
| 17 | Langue | Tout en français (doc, commentaires, logs, messages) ; noms de variables/fonctions en anglais |
| 18 | Interdits | Pas d'achat automatique, pas de connexion à un compte, pas d'IA à l'exécution, rien de payant |
| 19 | Sécurité | Dépôt public sans aucun secret (voir §10) |

## 4. Le produit et la page (constats vérifiés dans des exports réseau du 22/11/2026)

- **URL** : `https://www.playstation.com/fr-fr/ps5/playstation-digital-edition-console-model-group-slim/` (URL canonique de la page).
- **Nom** : « Console édition numérique PlayStation®5 (modèle - slim)* ».
- **Prix** : 499,99 EUR.
- **Identifiant produit** : `PSD001-PSDE01834_87-PS5DIGITAL3PVB7E`.
- **SKU** (identifiant de la référence de vente, comme un code-barres) : `PSD001-PSDE01834_87-PS5DIGITAL3PVB7E-E000O3L7E`. Présent aussi dans les balises `<meta name="productId">` et `<meta name="skus">` (avec `defaultProduct = true`).
- **Statut constaté ce jour** : indisponible.
- **Images** : balise `<meta name="image">` et champ `image` du JSON-LD (adresses `gmedia.playstation.com`). Éviter l'image `og:image`, qui est un visuel générique.

### 4.1 Signaux de disponibilité présents dans le HTML (indisponible, constatés)

1. **JSON-LD** : un bloc `<script type="application/ld+json">` de type `Product`, avec `offers.availability = "https://schema.org/OutOfStock"`, `price = "499.99"`, `priceCurrency = "EUR"`, `sku`, `name`, `image`, `url`.
2. **Bouton d'achat (données de la page)** : objet `GameCTA` pour le SKU, avec `"type":"UNAVAILABLE"`, `"hideCta":true` et `"priceOrText":"msgid_not_available_purchase"`. Ces données sont dans le HTML initial, à l'intérieur du flux de données Next.js (`self.__next_f.push(...)`), où les guillemets sont **échappés** (`\"`) : le parsing doit en tenir compte.
3. **Texte visible** : « Non disponible à l'achat » dans l'élément `data-qa="mfeCtaMain#offer0#finalPrice"`.

### 4.2 Ce qu'on ne connaît pas encore ⚠️

- La valeur de `availability` quand le produit est en stock (probablement `https://schema.org/InStock`).
- La valeur de `type` du bouton quand il est disponible (autre que `UNAVAILABLE`).
- Le texte du bouton quand il est disponible (probablement « Ajouter au panier »).
- Un témoignage isolé sur Reddit évoque un bouton « Ajouter au panier » pour une PS5 disponible, à côté d'une PS5 Pro « Non disponible à l'achat ». Le texte « Ajouter au panier » existe aussi dans le dictionnaire de traductions de la page (`msgid_add_cart`) : **sa seule présence dans la page ne prouve rien**.
- ⚠️ Un simple `requests` reçoit-il le **même HTML** qu'un navigateur ? Les exports viennent d'un navigateur. À tester en premier (blocage possible : 403, page de défi anti-robot).
- ⚠️ Fraîcheur : la page contient `<meta name="wraith-generated-at">` (date de génération). La page peut être mise en cache côté serveur : mesurer le délai réel entre un changement de stock et sa visibilité.

### 4.3 Piège : page « groupe de modèles »

Cette page regroupe plusieurs SKU (packs avec jeux : Fortnite, Call of Duty, Astro Bot, etc.) dont les identifiants apparaissent dans le HTML. Mais **seul le SKU de la console seule porte des données de disponibilité** (blocs `GameCTA` et `availability`). Le programme doit lire les champs **du SKU configuré** et ignorer les autres, pour ne jamais alerter à cause d'un pack.

### 4.4 Information utile pour plus tard (page liste)

La page `https://www.playstation.com/fr-fr/consoles/ps5/shop-all/` contient dans son HTML les **20 premiers produits sur 28** (identifiant, nom, prix, images, SKU) mais **aucune information de stock**, et pas d'URL de fiche. Elle ne sert donc pas à détecter le stock. Pour surveiller d'autres produits, il faudra l'URL de leur fiche (ex. `/fr-fr/ps5/ps5-pro/buy-now/` pour la PS5 Pro).

## 5. Règles de statut

Signaux : **A** = `availability` du JSON-LD ; **T** = `type` du bouton du SKU ; **X** = texte visible du bouton. Toutes les chaînes recherchées sont dans une liste de configuration, comparaison insensible à la casse, aux accents et aux apostrophes typographiques.

- **INDISPONIBLE** : A se termine par `OutOfStock` **ou** T = `UNAVAILABLE` **ou** X contient « Non disponible à l'achat », et aucun signal positif ne contredit.
- **DISPONIBLE** : A se termine par `InStock` (ou autre valeur positive de la liste) **ou** T est une valeur positive connue **ou** X contient « Ajouter au panier », et aucun signal négatif ne contredit.
- **INCONNU** : aucun signal reconnu, signaux contradictoires (par ex. `OutOfStock` et `InStock`), ou page inexploitable mais non vide.
- L'utilisateur enrichira les listes de signaux après quelques jours d'observation (ex. valeurs comme `LimitedAvailability`, `PreOrder`, autres types de bouton). Toute valeur non reconnue doit être **journalisée en entier** pour faciliter cet enrichissement.

### Quand envoyer un message

| Situation | Action |
|---|---|
| `INDISPONIBLE → DISPONIBLE` | Message immédiat « Disponible » |
| `INDISPONIBLE → INCONNU` | Message immédiat « Statut inconnu, vérifie la page » |
| Reste `DISPONIBLE` ou `INCONNU` | Rappel toutes les 30 min (« Toujours disponible ») |
| Retour à `INDISPONIBLE` | Pas de message ; mise à jour de l'état ; remise à zéro du minuteur |
| Produit absent de l'état (premier lancement ou ajout) | Traité comme s'il était `INDISPONIBLE` avant |

Le rappel de 30 minutes est arrondi au cycle de 5 minutes suivant.

### Garde-fous

- Page non récupérée, vide ou erreur HTTP : **échec de cycle** → l'état n'est pas modifié, aucune notification.
- Si une page est récupérée mais qu'aucun des trois signaux (A, T, X) n'est trouvé : statut `INCONNU` notifié **une seule fois** (pas de spam), avec un avertissement dans les logs (probable changement de structure du site).
- Pas de fausse alerte sur de l'absence de données : jamais de « disponible » sans un signal positif.

## 6. Message Telegram

- API HTTP Telegram (`sendMessage`, ou `sendPhoto` si image) via `requests`. `parse_mode=HTML` avec échappement des caractères spéciaux.
- Contenu : emoji + statut (Disponible / Statut inconnu / Toujours disponible), titre, prix, SKU, date et heure (Europe/Paris), lien.
- **Bouton cliquable** : `reply_markup` avec `inline_keyboard` et un bouton `url` « Acheter » vers la page produit.
- Si l'envoi de la photo échoue → renvoyer un message texte simple. Gérer 429 (`retry_after`) et timeouts avec un retry limité.
- `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID` viennent de variables d'environnement.

## 7. Architecture et hébergement

- **GitHub Actions** : workflow planifié (`schedule`) toutes les 5 minutes + `workflow_dispatch`. Éviter les minutes « rondes » (par ex. `3,8,13,18,23,28,33,38,43,48,53,58 * * * *`) ; les cron GitHub sont « au mieux » et parfois retardés.
- Dépôt **public** : minutes gratuites illimitées. Le nombre de requêtes n'est pas la contrainte ; ce sont les minutes d'exécution, et une page se charge en 1 à 2 s.
- **Une exécution = un contrôle** : jitter (0 à 30 s, configurable) → pour chaque produit de la liste (pause aléatoire de quelques secondes entre deux) → récupération → statut → notifications → sauvegarde de l'état → fin.
- **Persistance** : `state.json` restauré et sauvegardé à chaque exécution (cache Actions, ou commit sur une branche dédiée `state` ; l'IA choisit la plus fiable et justifie). Utiliser `concurrency` pour empêcher deux exécutions simultanées.
- GitHub désactive les workflows planifiés d'un dépôt public après **60 jours d'inactivité** : documenter la réactivation dans le README.

### Arborescence proposée

```
ps5-watcher/
├── .github/workflows/check.yml
├── config/products.json   # liste des produits : nom, url, sku
├── src/
│   ├── main.py        # orchestre un cycle
│   ├── fetcher.py     # téléchargement de la page (retries, en-têtes)
│   ├── parser.py      # extraction JSON-LD, bouton, texte, image
│   ├── status.py      # règles de statut (signaux)
│   ├── notifier.py    # envoi Telegram
│   ├── state.py       # lecture/écriture de state.json
│   └── config.py      # constantes, signaux, variables d'environnement
├── tests/             # sur HTML d'exemple sauvegardés (indisponible, et disponible simulé)
├── state.json
├── requirements.txt
├── .env.example       # modèle sans valeurs réelles
├── .gitignore         # contient .env
├── README.md
└── order.md
```

Exemple de `config/products.json` :
```json
[
  {
    "name": "PS5 Édition numérique (Slim)",
    "url": "https://www.playstation.com/fr-fr/ps5/playstation-digital-edition-console-model-group-slim/",
    "sku": "PSD001-PSDE01834_87-PS5DIGITAL3PVB7E-E000O3L7E"
  }
]
```

## 8. Méthode de récupération

1. **Étape 1 (à valider d'abord)** : `requests.get(url, headers=...)` et vérifier que la réponse contient le JSON-LD, le SKU et le bloc `GameCTA` (voir §4). Si oui : utiliser cette méthode (JSON-LD via `json.loads` ; bloc `GameCTA` via expression régulière tenant compte des guillemets échappés).
2. **Si la réponse diffère du navigateur** (403, page de défi, contenu vide) : essayer des en-têtes de navigateur plus complets (`User-Agent`, `Accept`, `Accept-Language: fr-FR`).
3. **Dernier recours** : Playwright (navigateur headless), gratuit mais plus lourd, sur GitHub Actions.

Extraction par produit : titre, prix + devise, lien, URL de l'image, SKU, A, T, X, statut, et texte brut des signaux pour le débogage.

## 9. Programmation défensive (exigence forte)

Le programme ne doit **jamais** s'arrêter brutalement ni corrompre l'état.

- Timeouts sur toutes les requêtes ; 3 essais avec backoff croissant (5 s, 15 s, 45 s) + jitter ; gestion spécifique de 403, 429 (`Retry-After`), 5xx. Après épuisement des essais : le cycle du produit est abandonné proprement.
- Réponse vide, HTML ou JSON invalide, champ manquant, structure modifiée : journaliser et continuer.
- Un `try/except` **par produit**.
- Si l'envoi Telegram échoue, ne pas mettre à jour la date de dernier message (nouvel essai au cycle suivant).
- Écriture atomique de `state.json` (fichier temporaire puis renommage) ; fichier absent ou corrompu → repartir d'un état vide.
- Variables d'environnement manquantes : erreur claire dans les logs.
- Code de sortie 0 quand le cycle s'est bien déroulé (même sans notification) ; non nul seulement en cas d'erreur de configuration ou d'échecs répétés, pour que GitHub envoie un e-mail.
- Logs avec `logging` : un résumé par cycle (produits, statut, valeurs brutes de A/T/X, notifications). **Ne jamais écrire le token.**
- Options de test : `--dry-run` (n'envoie rien), `--force-notify` (simule un produit disponible pour tester le message et le bouton), et un test automatique sur un HTML d'exemple « disponible » fabriqué.
- Respecter les CGU et `robots.txt` (à vérifier), fréquence modérée.

## 10. Sécurité d'un dépôt public

- Le token Telegram et le `chat_id` vont **uniquement** dans *Settings → Secrets and variables → Actions* (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
- `.env` est dans `.gitignore` ; le dépôt ne contient qu'un `.env.example` sans valeur.
- Avant chaque commit, vérifier qu'aucun token n'apparaît dans le code, les tests ou les logs.
- Si le token fuite : le révoquer immédiatement avec `/revoke` dans @BotFather et en générer un nouveau.
- Workflow avec permissions minimales (`permissions: contents: write` seulement si l'état est commité) et pas d'exécution de code provenant de forks.
- Le dépôt public révèle quel produit est surveillé : accepté par l'utilisateur.

## 11. Étapes de réalisation (🧑 = utilisateur, 🤖 = IA agent)

**Étape 0 — Préparation**
- 🧑 Compte GitHub gratuit, Python 3.14, Git, VS Code avec Copilot.

**Étape 1 — Bot Telegram** (guider pas à pas, l'utilisateur n'a jamais fait ça)
- 🧑 Dans Telegram : @BotFather → `/newbot` → nom + identifiant finissant par `bot` → copier le **token** (secret).
- 🧑 Envoyer un message à son bot.
- 🤖 Expliquer comment obtenir le `chat_id` (via `getUpdates`) et fournir un script de test d'envoi.
- 🧑 Confirmer la réception.

**Étape 2 — Validation de la récupération**
- 🤖 Tester `requests` sur l'URL (voir §8) et dire ce qui est reçu : JSON-LD, SKU, `GameCTA`, `availability`.
- 🧑 Si ça échoue : fournir un export HAR avec le filtre « Tout » (F12 → Réseau → « Conserver le journal » → recharger → clic droit → « Enregistrer tout au format HAR avec contenu »).

**Étape 3 — Développement**
- 🤖 Créer l'arborescence, le code et les tests (fichiers HTML d'exemple, y compris un « disponible » simulé).
- 🧑 Créer `.env` local, lancer `--dry-run` puis `--force-notify`, remonter les erreurs complètes (traceback).

**Étape 4 — Mise en ligne**
- 🧑 Créer un dépôt **public**, y envoyer le code, ajouter les deux Secrets.
- 🤖 Écrire `check.yml`.
- 🧑 Lancer le workflow à la main et lire les logs dans l'onglet Actions.

**Étape 5 — Validation (24 à 48 h)**
- Vérifier : exécutions planifiées, état conservé entre runs, pas de doublon, rappels à 30 min, bouton cliquable, valeurs réelles de A/T/X dans les logs.

**Étape 6 — Observation et maintenance**
- 🧑 Quelques jours après : relire les logs, ajouter les nouvelles valeurs de signaux à la configuration, surveiller les e-mails d'échec GitHub, réactiver le workflow après 60 jours d'inactivité.
- 🧑 Plus tard : ajouter d'autres produits dans `config/products.json`.

## 12. Critères d'acceptation

1. Exécution automatique toutes les ~5 minutes sur GitHub Actions (retards tolérés).
2. Le statut du SKU configuré est lu à partir de `availability` et `type` (et du texte en secours), sans confondre avec les packs de la même page.
3. Passage indisponible → disponible : un message avec titre, prix, lien, image, SKU, statut, date/heure et bouton cliquable.
4. Rappel toutes les 30 minutes tant que le produit reste disponible ; aucun message tant qu'il est indisponible.
5. Le statut inconnu déclenche une notification marquée comme telle (sans répétition inutile).
6. Aucune panne (réseau, 403/429, JSON invalide, erreur Telegram) ne plante le cycle ni ne corrompt l'état.
7. Ajouter un produit = ajouter une entrée dans `config/products.json`, sans modifier le code.
8. Aucun secret dans le dépôt ni dans les logs ; aucun coût ; aucune IA à l'exécution ; aucun achat automatique.

## 13. Questions ouvertes

- `requests` obtient-il le même HTML que le navigateur ?
- Quelles valeurs prennent `availability`, `type` et le texte du bouton quand le produit est en stock ?
- Quel est le délai réel (cache) entre un changement de stock et sa visibilité dans la page ?
- Cache Actions ou branche `state` pour l'état ?

## 14. Glossaire

- **SKU** : identifiant interne d'une référence de vente (comme un code-barres).
- **JSON-LD** : bloc de données structurées intégré à la page, lisible par les robots.
- **HAR** : enregistrement des requêtes réseau d'une page, exporté depuis le navigateur.
- **Jitter** : petit délai aléatoire pour que les requêtes ne soient pas parfaitement régulières.
- **Backoff** : attente de plus en plus longue entre deux essais après une erreur.
- **Cron** : planification d'une tâche à intervalles réguliers.
- **Headless** : navigateur piloté par programme, sans fenêtre visible.
- **Secrets GitHub** : variables chiffrées utilisables par le workflow sans apparaître dans le code.

## 15. Consignes de comportement pour l'IA

- Réponds en français, de façon courte et structurée ; explique simplement les notions nouvelles ; décide des choix techniques à la place de l'utilisateur en les justifiant en une phrase.
- Ne devine pas la structure du site : teste et signale ce qui reste hypothèse (⚠️).
- Signale clairement les actions requises de l'utilisateur (🧑).
- Avance étape par étape ; ne passe pas à la suivante sans que la précédente fonctionne.
- Reste dans le périmètre : notification seule, gratuit, sans IA à l'exécution.
