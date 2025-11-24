# MangaReader Architecture

## Vue d'ensemble

Cette architecture modulaire permet un développement maintenable et extensible de l'application MangaReader. L'application utilise FastAPI pour le backend, SQLModel pour l'accès aux données, et un système d'authentification basé sur les sessions.

## Structure des fichiers

```
src/reader/
├── static/
│   ├── css/
│   │   ├── base.css            # Styles de base et variables
│   │   ├── layout.css          # Layout général
│   │   ├── nav.css             # Navigation
│   │   ├── hero.css            # Sections héroïques
│   │   ├── chapters.css        # Styles pour chapitres
│   │   ├── manga-list.css      # Liste des mangas
│   │   ├── footer.css          # Footer
│   │   ├── links.css           # Liens et boutons
│   │   ├── components.css      # Styles pour composants JS
│   │   └── forms.css           # Styles pour formulaires
│   └── js/
│       ├── config.js            # Configuration centralisée
│       ├── utils.js             # Fonctions utilitaires
│       ├── navigation.js       # Gestion navigation mobile
│       ├── images.js            # Gestion images/couvertures
│       ├── chapter-viewer.js    # Visualiseur de chapitres
│       ├── add-manga.js         # Gestion formulaire ajout manga
│       └── main.js              # Module principal
│
├── templates/
│   ├── base.html                # Template de base
│   ├── index.html               # Liste des mangas
│   ├── library.html             # Bibliothèque complète
│   ├── manga_index.html         # Page détail manga
│   ├── chapter.html             # Visualiseur de chapitres
│   ├── add_manga.html           # Formulaire ajout manga
│   └── login.html               # Page de connexion
│
├── ARCHITECTURE.md               # Cette documentation
└── app.py                       # Application FastAPI
```

## Modules JavaScript

### 1. config.js
Configuration centralisée de l'application :
- Paramètres de l'application
- Endpoints API
- Configuration UI (breakpoints, animations)
- Messages d'erreur et de succès
- Raccourcis clavier
- Gestion des paramètres utilisateur

### 2. utils.js
Fonctions utilitaires réutilisables :
- `debounce()` / `throttle()` pour optimiser les performances
- `isInViewport()` pour la détection de visibilité
- `getDeviceType()` pour la détection d'appareil
- `formatFileSize()` pour l'affichage des tailles
- `storage` pour la gestion du localStorage
- `showNotification()` pour les notifications utilisateur

### 3. navigation.js
Gestion de la navigation mobile :
- Menu hamburger avec animations
- Fermeture automatique du menu
- Gestion des événements clavier
- Responsive design
- Accessibilité

### 4. images.js
Gestion des images :
- Chargement des couvertures avec fallback
- Lazy loading
- Préchargement d'images
- États de chargement
- Gestion des erreurs

### 5. chapter-viewer.js
Visualiseur de chapitres :
- Navigation clavier (flèches, T/B, F, Escape)
- Suivi de progression de lecture
- Mode plein écran
- Auto-scroll
- Sauvegarde de la progression

### 6. add-manga.js
Gestion du formulaire d'ajout de manga :
- Prévisualisation du nom de dossier généré
- Validation en temps réel de l'URL
- Détection automatique de la scanlation group
- Comptage des chapitres disponibles
- Gestion interactive des tags
- Synchronisation des tags sélectionnés

### 7. main.js
Module principal qui orchestre tous les autres :
- Initialisation des modules
- Gestion des événements globaux
- Tracking des événements
- Gestion des erreurs
- API publique pour les autres modules

## Templates HTML

### base.html
Template de base qui contient :
- Structure HTML commune
- Navigation avec menu hamburger
- Inclusion des fichiers CSS et JS
- Métadonnées

### index.html
Liste des mangas suivis :
- Grille responsive des mangas
- Cartes avec couvertures
- Informations et actions

### manga_index.html
Page de détail d'un manga :
- Affichage desktop/mobile adaptatif
- Informations du manga
- Liste des chapitres
- Boutons d'action

### chapter.html
Visualiseur de chapitres :
- Barre d'outils de navigation
- Affichage des pages
- Indicateur de progression
- Module JavaScript spécifique

### add_manga.html
Formulaire d'ajout de manga :
- Formulaire principal avec validation
- Sidebar avec prévisualisation
- Gestion des tags disponibles
- Formulaire de création de tags
- Validation en temps réel de l'URL
- Affichage du nombre de chapitres trouvés

### login.html
Page de connexion :
- Formulaire d'authentification
- Gestion des erreurs
- Redirection après connexion

## Styles CSS

### base.css
Styles de base :
- Variables CSS (couleurs, espacements, ombres)
- Reset et normalisation
- Typographie de base

### layout.css
Layout général :
- Structure de page
- Conteneurs et grilles
- Espacements

### nav.css
Navigation :
- Menu hamburger
- Navigation responsive
- États actifs

### hero.css
Sections héroïques :
- Layout adaptatif desktop/mobile
- Affichage des couvertures
- Informations manga

### chapters.css
Styles pour chapitres :
- Liste des chapitres
- Navigation entre chapitres

### manga-list.css
Liste des mangas :
- Grille responsive
- Cartes manga
- États hover

### forms.css
Styles pour formulaires :
- Grille de formulaire
- Champs de saisie
- Validation visuelle
- États de statut (success/error/neutral)
- Tags interactifs
- Sidebar de prévisualisation

### components.css
Styles pour composants JavaScript :
- États de chargement
- Animations
- Notifications
- Améliorations interactives
- Support accessibilité

## Authentification

### Système d'authentification
L'application utilise un système d'authentification basé sur les sessions avec bcrypt pour le hachage des mots de passe.

#### Middleware
- **SessionMiddleware** : Gère les sessions utilisateur (cookie-based)
- **AuthMiddleware** : Vérifie l'authentification pour les routes protégées
- Routes publiques : `/login`, `/logout`, `/static/*`
- Routes protégées : Toutes les autres routes nécessitent une authentification

#### Flux d'authentification
1. Utilisateur accède à une route protégée
2. `AuthMiddleware` vérifie la session
3. Si non authentifié → redirection vers `/login`
4. Après connexion réussie → session créée avec `user_id`
5. Les routes suivantes utilisent `get_current_user` pour récupérer l'utilisateur

#### Dépendances FastAPI
- `get_current_user` : Dependency qui récupère l'utilisateur depuis la session
- `get_user_repository` : Repository pour l'accès aux données utilisateur

## API Routes

### Routes publiques
- `GET /login` : Page de connexion
- `POST /login` : Traitement de la connexion
- `GET /logout` : Déconnexion

### Routes protégées (nécessitent authentification)

#### Navigation
- `GET /` : Liste des mangas suivis (accueil)
- `GET /library` : Bibliothèque complète des mangas

#### Manga
- `GET /manga/{manga_id}` : Détails d'un manga
- `GET /manga/{manga_id}/cover` : Image de couverture
- `GET /add_manga` : Formulaire d'ajout de manga
- `POST /add_manga` : Création d'un nouveau manga
- `GET /add_manga/validate` : Validation d'URL et comptage de chapitres (JSON)

#### Chapitres
- `GET /{manga_id}/chapter/{chapter_number}` : Visualisation d'un chapitre
- `GET /image/{manga_id}/image/{page_id}` : Affichage d'une page

#### Tags
- `POST /add_manga/tag` : Création d'un nouveau tag

## Intégration Scraper

### Validation d'URL
Chaque scraper implémente `validate_url_and_get_chapter_count()` :
- Vérifie que l'URL pointe vers un manga valide
- Compte le nombre de chapitres disponibles
- Retourne un tuple `(is_valid, chapter_count, error_message)`

### Scrapers supportés
- **AsuraScansScraper** : Pour les mangas d'Asura Scans
- **MangaFireToScraper** : Pour les mangas de MangaFire

### Création de manga
1. Validation des données du formulaire
2. Vérification des doublons (nom et URL)
3. Validation de l'URL avec le scraper approprié
4. Création du dossier local
5. Création de l'entrée dans la base de données
6. Les chapitres seront ajoutés lors du prochain scan

## Flux de données

1. **Authentification** : `AuthMiddleware` vérifie la session
2. **Chargement de page** : `main.js` initialise les modules
3. **Navigation** : `navigation.js` gère le menu mobile
4. **Images** : `images.js` charge les couvertures avec fallback
5. **Chapitres** : `chapter-viewer.js` gère la lecture
6. **Ajout manga** : `add-manga.js` gère la validation et le formulaire
7. **Configuration** : `config.js` fournit les paramètres
8. **Utilitaires** : `utils.js` fournit les fonctions communes

## Raccourcis clavier

### Navigation générale
- `Escape` : Fermer le menu mobile

### Visualiseur de chapitres
- `←` / `→` : Navigation entre chapitres
- `T` : Aller en haut de page
- `B` : Aller en bas de page
- `F` : Mode plein écran
- `Escape` : Quitter le plein écran
- `Espace` : Auto-scroll
- `Home` / `End` : Haut/bas de page

## Fonctionnalités

### Authentification
- Système de connexion/déconnexion
- Sessions sécurisées avec cookies
- Hachage des mots de passe avec bcrypt
- Protection des routes par middleware
- Redirection automatique vers login si non authentifié

### Gestion des mangas
- Ajout manuel de mangas via formulaire
- Validation en temps réel de l'URL
- Comptage automatique des chapitres disponibles
- Détection automatique de la scanlation group
- Prévention des doublons (nom et URL)
- Création automatique du dossier local

### Gestion des tags
- Création de nouveaux tags
- Sélection interactive des tags
- Validation des tags existants
- Stockage dans `tags.json`

### Responsive Design
- Mobile-first approach
- Breakpoints : 768px (mobile), 1024px (tablet)
- Menu hamburger sur mobile
- Layouts adaptatifs
- Formulaires responsive

### Performance
- Lazy loading des images
- Debounce/throttle pour les événements
- Préchargement intelligent
- Gestion mémoire optimisée
- Validation asynchrone des URLs

### Accessibilité
- Support clavier complet
- Focus visible
- ARIA labels
- Support lecteurs d'écran
- Mode réduit (reduced motion)

### Persistance
- Sauvegarde progression de lecture
- Paramètres utilisateur
- Cache des images
- État de l'application
- Sessions utilisateur

## Extension

### Ajouter un nouveau module JavaScript
1. Créer le fichier dans `static/js/`
2. Exporter la classe via `window.NomModule`
3. L'initialiser dans `main.js`
4. Documenter l'API publique

### Ajouter des styles
1. Créer un nouveau fichier CSS si nécessaire ou utiliser `components.css`
2. Utiliser les variables CSS existantes de `base.css`
3. Tester la responsivité
4. Vérifier l'accessibilité

### Ajouter une nouvelle page
1. Créer le template qui étend `base.html`
2. Ajouter la route dans `app.py` avec `current_user: User = Depends(get_current_user)`
3. Créer un module JS spécifique si nécessaire
4. Ajouter les styles dans le fichier CSS approprié

### Ajouter un nouveau scraper
1. Créer une classe qui hérite de `BaseScraper` dans `src/scraper/`
2. Implémenter `validate_url_and_get_chapter_count(url)` :
   ```python
   def validate_url_and_get_chapter_count(self, url: str):
       try:
           response = self._get_from_url(url)
           soup = bs4.BeautifulSoup(response.content, "html.parser")
           chapters = self.get_chapter_links(soup)
           return True, len(chapters), ""
       except Exception as e:
           return False, 0, str(e)
   ```
3. Implémenter les méthodes nécessaires (`get_chapter_links`, `get_comic_cover`, etc.)
4. Ajouter le scraper dans `ScanlationGroup` enum
5. Ajouter la factory dans `SCRAPER_FACTORIES` dans `app.py`

### Ajouter une route protégée
1. Ajouter la route dans `app.py`
2. Utiliser `current_user: User = Depends(get_current_user)` comme paramètre
3. La route sera automatiquement protégée par `AuthMiddleware`
4. Si besoin d'une route publique, l'ajouter dans la liste des exceptions dans `AuthMiddleware`

## Base de données

### Modèles principaux
- **User** : Utilisateurs de l'application
- **Comic** : Mangas/comics avec métadonnées
- **Chapter** : Chapitres d'un manga
- **Page** : Pages individuelles d'un chapitre

### Repositories
- **UserRepository** : Gestion des utilisateurs
- **ComicRepository** : Gestion des mangas (CRUD, recherche, filtres)
- **ChapterRepository** : Gestion des chapitres
- **PageRepository** : Gestion des pages

### Accès aux données
- Utilisation de SQLModel pour l'ORM
- `DatabaseAccessLayer` pour la gestion des sessions
- Dependency injection via FastAPI pour les repositories

## Dépendances principales

### Backend
- **FastAPI** : Framework web moderne
- **SQLModel** : ORM basé sur SQLAlchemy et Pydantic
- **bcrypt** : Hachage des mots de passe
- **Starlette** : Middleware de sessions
- **Jinja2** : Templates HTML

### Frontend
- JavaScript vanilla (pas de framework)
- CSS moderne avec variables CSS
- Pas de dépendances externes pour le JavaScript

### Scrapers
- **requests** : Requêtes HTTP
- **beautifulsoup4** : Parsing HTML
- **certifi** : Certificats SSL

## Debugging

### Console
- Utiliser `console.log()` pour le debugging
- Les erreurs sont automatiquement loggées
- Les événements trackés sont stockés dans localStorage

### Configuration de debug
```javascript
// Activer le mode debug
AppConfig.set('app.debug', true);

// Voir les événements trackés
console.log(Utils.storage.get('tracked_events', []));

// Accéder aux modules
const app = window.app;
const navigation = app.getModule('navigation');
```

### Debugging backend
- Les erreurs FastAPI sont loggées automatiquement
- Utiliser `print()` pour le debugging Python
- Vérifier les sessions dans les cookies du navigateur
- Vérifier les logs de la base de données

## Bonnes pratiques

1. **Modularité** : Chaque module a une responsabilité spécifique
2. **Performance** : Utiliser debounce/throttle, lazy loading
3. **Accessibilité** : Gérer clavier, focus, ARIA
4. **Responsive** : Tester sur différentes tailles
5. **Gestion d'erreurs** : Toujours gérer les erreurs gracieusement
6. **Documentation** : Documenter les APIs publiques
7. **Tests** : Tester sur différents navigateurs et appareils
8. **Sécurité** :
   - Toujours valider les entrées utilisateur
   - Utiliser bcrypt pour les mots de passe
   - Protéger les routes sensibles avec authentification
   - Utiliser des variables d'environnement pour les secrets en production
9. **Validation** : Valider les données côté serveur ET côté client
10. **Sessions** : Ne jamais stocker d'informations sensibles dans les sessions
