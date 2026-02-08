# akiratv/metadata_fetcher.py
"""
Metadata fetching module for AkiraTV Collection Wizard
Handles online metadata retrieval from TMDB, Wikipedia, and IMDb
"""

import re
import requests
import urllib.parse
from datetime import datetime
from pathlib import Path
import time

class MetadataFetcher:
    def __init__(self, covers_dir=None):
        """Initialize the metadata fetcher"""
        self.covers_dir = covers_dir or Path(__file__).parent.parent / "user" / "covers"
        self.covers_dir.mkdir(parents=True, exist_ok=True)
        
        # TMDB configuration
        self.tmdb_api_key = ""
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.tmdb_image_base_url = "https://image.tmdb.org/t/p/w500"
    
    def set_tmdb_api_key(self, api_key):
        """Set the TMDB API key"""
        self.tmdb_api_key = api_key

    def search_tmdb_movie(self, title, year=None, search_hints=None):
        """Search for movie on TMDB"""
        if not self.tmdb_api_key:
            return None

        try:
            # Clean up the title for better search results
            clean_title = re.sub(r'\b(1080p|720p|2160p|4k|bluray|webrip|bdrip|dvdrip|x264|x265|h264|h265)\b', '', title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\b(fmp4|mp4|mkv|avi|mov|webm|remux|remastered|extended|uncut)\b', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'[._\-]', ' ', clean_title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()

            # Parse search hints to extract year and names
            hints_year, hints_names = self._parse_search_hints(search_hints)

            # Use year from hints if not provided directly
            search_year = year if year else hints_year

            # Search for the movie with clean title (no hints appended)
            search_url = f"{self.tmdb_base_url}/search/movie"
            params = {
                "api_key": self.tmdb_api_key,
                "query": clean_title
            }

            if search_year:
                params["year"] = search_year
                print(f"DEBUG: TMDB searching for '{clean_title}' with year {search_year}")
            else:
                print(f"DEBUG: TMDB searching for '{clean_title}'")

            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            print(f"DEBUG: TMDB found {len(results)} results")

            if results:
                # If we have search hints, filter/rank results by cast matching
                if hints_names:
                    print(f"DEBUG: Filtering results by hints names: {hints_names}")
                    best_match = self._find_best_match_with_hints(results, hints_names)
                    if best_match:
                        movie = best_match
                        print(f"DEBUG: Selected best match based on hints: {movie.get('title', 'Unknown')}")
                    else:
                        movie = results[0]
                        print(f"DEBUG: No hints match found, using first result: {movie.get('title', 'Unknown')}")
                else:
                    movie = results[0]

                # Get detailed movie info
                movie_id = movie["id"]
                detail_url = f"{self.tmdb_base_url}/movie/{movie_id}"
                detail_params = {"api_key": self.tmdb_api_key}

                detail_response = requests.get(detail_url, params=detail_params, timeout=10)
                detail_response.raise_for_status()

                return detail_response.json()

            return None

        except Exception as e:
            print(f"Error searching TMDB: {e}")
            return None

    def _parse_search_hints(self, search_hints):
        """Parse search hints to extract year and actor/director names"""
        if not search_hints:
            return None, None

        hints_text = search_hints.strip()
        extracted_year = None
        names = []

        # Try to extract year from hints (e.g., "1996", "year 1996", "(1996)")
        year_patterns = [
            r'\byear\s*(\d{4})\b',
            r'\(\s*(\d{4})\s*\)',
            r'\b(\d{4})\b'
        ]

        for pattern in year_patterns:
            year_match = re.search(pattern, hints_text, re.IGNORECASE)
            if year_match:
                year = int(year_match.group(1))
                if 1900 <= year <= 2030:  # Valid year range
                    extracted_year = year
                    # Remove year from hints text
                    hints_text = re.sub(pattern, '', hints_text, count=1, flags=re.IGNORECASE)
                    break

        # Parse remaining text for names (comma-separated)
        if hints_text:
            # Clean up the hints text
            names_text = re.sub(r'\s+', ' ', hints_text).strip()
            # Split by comma
            names = [name.strip() for name in names_text.split(',') if name.strip()]

        return extracted_year, names

    def _find_best_match_with_hints(self, results, hints_names):
        """Find best matching result based on search hints (actor/director names)"""
        # Convert single string to list for backward compatibility
        if isinstance(hints_names, str):
            hints_names = [hints_names]

        # Convert all names to lowercase for matching
        hints_lower_list = [name.lower() for name in hints_names]
        best_match = None
        best_score = 0

        for movie in results:
            score = 0
            movie_id = movie.get("id")

            try:
                # Get credits to check cast
                credits_url = f"{self.tmdb_base_url}/movie/{movie_id}/credits"
                credits_params = {"api_key": self.tmdb_api_key}
                credits_response = requests.get(credits_url, params=credits_params, timeout=10)
                credits_response.raise_for_status()
                credits_data = credits_response.json()

                # Check cast names against each hint
                for cast_member in credits_data.get("cast", [])[:5]:  # Top 5 cast
                    cast_name_lower = cast_member.get("name", "").lower()
                    for hint_lower in hints_lower_list:
                        if hint_lower in cast_name_lower:
                            score += 10
                            print(f"DEBUG: Found cast match: {cast_member.get('name')} for hint: {hint_lower}")

                # Check crew (director, etc.)
                for crew_member in credits_data.get("crew", []):
                    crew_name_lower = crew_member.get("name", "").lower()
                    for hint_lower in hints_lower_list:
                        if hint_lower in crew_name_lower:
                            job = crew_member.get("job", "").lower()
                            if "director" in job:
                                score += 15
                                print(f"DEBUG: Found director match: {crew_member.get('name')} for hint: {hint_lower}")
                            else:
                                score += 5

            except Exception as e:
                print(f"DEBUG: Error fetching credits for movie {movie_id}: {e}")

            if score > best_score:
                best_score = score
                best_match = movie

        print(f"DEBUG: Best match score: {best_score} for {best_match.get('title', 'None') if best_match else 'None'}")
        return best_match if best_score > 0 else None
    def search_wikipedia_movie(self, title, year=None, search_hints=None):
        """Search for movie information on Wikipedia"""
        try:
            # Clean up the title for better search results
            clean_title = re.sub(r'\b(1080p|720p|2160p|4k|bluray|webrip|bdrip|dvdrip|x264|x265|h264|h265)\b', '', title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\b(fmp4|mp4|mkv|avi|mov|webm|remux|remastered|extended|uncut)\b', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\b(dd5\.1|aac|ac3|dts|flac)\b', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'[._\-]', ' ', clean_title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()

            # Remove "film" or "movie" if already in the title to avoid duplication
            if clean_title.lower().endswith(' film'):
                clean_title = clean_title[:-5].strip()
            elif clean_title.lower().endswith(' movie'):
                clean_title = clean_title[:-6].strip()

            # Parse search hints to extract year and names
            hints_year, hints_names = self._parse_search_hints(search_hints)

            # Use year from hints if not provided directly
            search_year = year if year else hints_year

            # Try different search variations - clean title only (no hints in search)
            search_terms = []

            if search_year:
                # Most specific searches first
                search_terms.extend([
                    f"{clean_title} ({search_year} film)",
                    f"{clean_title} {search_year} film",
                    f"{clean_title} ({search_year})",
                ])

            # General searches
            search_terms.extend([
                f"{clean_title} film",
                f"{clean_title} movie",
                clean_title
            ])

            if hints_names:
                print(f"DEBUG: Wikipedia will filter results by hints: {hints_names}")
            
            # Set proper headers for Wikipedia API
            headers = {
                'User-Agent': 'AkiraTV Collection Manager/1.0 (https://github.com/your-repo; your-email@example.com)'
            }
            
            for search_term in search_terms:
                print(f"DEBUG: Searching Wikipedia for: '{search_term}'")
                
                # Use Wikipedia's OpenSearch API
                search_url = "https://en.wikipedia.org/w/api.php"
                search_params = {
                    "action": "opensearch",
                    "search": search_term,
                    "limit": 10,  # Get more results to find better matches
                    "namespace": 0,
                    "format": "json"
                }
                
                response = requests.get(search_url, params=search_params, headers=headers, timeout=10)
                response.raise_for_status()
                
                search_results = response.json()
                print(f"DEBUG: Wikipedia search results: {search_results}")
                
                if len(search_results) >= 2 and search_results[1]:  # Check if we have results
                    titles = search_results[1]
                    
                    # Look for the best match with priority system
                    best_match = None
                    best_score = 0
                    
                    # Normalize clean title for matching
                    clean_title_normalized = re.sub(r'[^\w\s]', '', clean_title.lower())
                    clean_title_normalized = re.sub(r'\s+', ' ', clean_title_normalized).strip()
                    
                    for result_title in titles:
                        score = 0
                        result_lower = result_title.lower()
                        result_normalized = re.sub(r'[^\w\s]', '', result_lower)
                        result_normalized = re.sub(r'\s+', ' ', result_normalized).strip()

                        # Skip soundtrack/score albums
                        if any(skip in result_lower for skip in ['soundtrack', 'film score', 'score album', 'original motion picture score']):
                            print(f"DEBUG: Skipping soundtrack/score: '{result_title}'")
                            score -= 100  # Heavy penalty

                        # Scoring system for better matches
                        if search_year and f"({search_year}" in result_title:
                            score += 100  # Exact year match is highest priority
                        elif search_year and str(search_year) in result_title:
                            score += 50   # Year mentioned somewhere

                        if "film)" in result_lower:
                            score += 30   # Proper film disambiguation
                        elif "film" in result_lower:
                            score += 20   # Contains film
                        elif "movie" in result_lower:
                            score += 15   # Contains movie

                        # Option D: Check if result starts with search title (ignoring punctuation)
                        if result_normalized.startswith(clean_title_normalized):
                            score += 150
                            print(f"DEBUG: Title starts with match bonus: +150")

                        # Exact title match bonus (normalized)
                        if clean_title_normalized in result_normalized:
                            score += 25
                        
                        # Near-exact match bonus
                        if clean_title_normalized == result_normalized:
                            score += 200
                            print(f"DEBUG: Exact match bonus: +200")

                        # Check for hints in the result title
                        if hints_names:
                            for hint in hints_names:
                                hint_normalized = re.sub(r'[^\w\s]', '', hint.lower())
                                if hint_normalized in result_normalized:
                                    score += 20
                                    print(f"DEBUG: Hint '{hint}' found in title '{result_title}': +20")
                        
                        # PENALTY for partial matches - if result has many extra words
                        result_word_count = len(result_normalized.split())
                        clean_word_count = len(clean_title_normalized.split())
                        if result_word_count > clean_word_count + 2:
                            penalty = (result_word_count - clean_word_count - 2) * 15
                            score -= penalty
                            print(f"DEBUG: Partial match penalty: -{penalty}")

                        # Avoid disambiguation pages unless they're film-specific
                        if result_title == clean_title and not any(keyword in result_lower for keyword in ['film', 'movie']):
                            score -= 10  # Likely a disambiguation page

                        print(f"DEBUG: '{result_title}' scored {score}")

                        if score > best_score:
                            best_score = score
                            best_match = result_title
                    
                    if best_match:
                        print(f"DEBUG: Best match: {best_match} (score: {best_score})")
                        # Get the full page content
                        result = self.get_wikipedia_page_info(best_match)
                        if result:
                            return result
                    else:
                        print("DEBUG: No good matches found in this search")
            
            print("DEBUG: No Wikipedia results found for any search term")
            return None
            
        except Exception as e:
            print(f"Error searching Wikipedia: {e}")
            return None

    def search_omdb_movie(self, title, year=None, api_key=None, search_hints=None):
        """Search for movie using OMDB API (requires API key)"""
        if not api_key:
            print("DEBUG: OMDB API key not provided")
            return None
            
        try:
            # Clean title
            clean_title = re.sub(r'\b(1080p|720p|2160p|4k|bluray|webrip|bdrip|dvdrip|x264|x265|h264|h265)\b', '', title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\b(fmp4|mp4|mkv|avi|mov|webm|remux|remastered|extended|uncut)\b', '', clean_title, flags=re.IGNORECASE)
            # Remove part numbers like "1", "2", etc. from title for better searching
            clean_title = re.sub(r'\s*\d+$', '', clean_title).strip()
            clean_title = re.sub(r'[._\-]', ' ', clean_title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            
            print(f"DEBUG: Searching OMDB for: '{clean_title}'")
            
            # OMDB API endpoint
            url = "http://www.omdbapi.com/"
            params = {
                "t": clean_title,
                "apikey": api_key,
                "type": "movie",
                "plot": "full"
            }
            
            # Parse search hints to extract year
            if search_hints:
                hints_year, _ = self._parse_search_hints(search_hints)
                if hints_year and not year:
                    year = hints_year
                    print(f"DEBUG: Using year from search hints: {year}")
            
            if year:
                params["y"] = year
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("Response") == "True":
                # Parse genres
                genres = []
                if data.get("Genre"):
                    genres = [{"name": g.strip()} for g in data["Genre"].split(",") if g.strip()]
                
                result = {
                    "title": data.get("Title", clean_title),
                    "overview": data.get("Plot", ""),
                    "release_date": data.get("Year", str(year) if year else str(datetime.now().year)),
                    "genres": genres,
                    "poster_path": data.get("Poster") if data.get("Poster") != "N/A" else None,
                    "source": "OMDB",
                    "imdb_id": data.get("imdbID"),
                    "rating": data.get("Rated", "NR"),
                    "director": data.get("Director", ""),
                    "actors": data.get("Actors", "")
                }
                print(f"DEBUG: Found movie via OMDB: {result['title']} ({result['release_date']})")
                return result
            else:
                print(f"DEBUG: OMDB returned error: {data.get('Error', 'Unknown error')}")
                # If exact match failed, try search instead of title search
                print(f"DEBUG: Trying OMDB search for: '{clean_title}'")
                search_params = {
                    "s": clean_title,
                    "apikey": api_key,
                    "type": "movie"
                }
                if year:
                    search_params["y"] = year
                search_response = requests.get(url, params=search_params, timeout=10)
                search_response.raise_for_status()
                search_data = search_response.json()
                if search_data.get("Response") == "True" and search_data.get("Search"):
                    # Get first result
                    first_result = search_data["Search"][0]
                    # Get detailed info for first result
                    details_params = {
                        "i": first_result["imdbID"],
                        "apikey": api_key,
                        "plot": "full"
                    }
                    details_response = requests.get(url, params=details_params, timeout=10)
                    details_response.raise_for_status()
                    details_data = details_response.json()
                    if details_data.get("Response") == "True":
                        genres = []
                        if details_data.get("Genre"):
                            genres = [{"name": g.strip()} for g in details_data["Genre"].split(",") if g.strip()]
                        result = {
                            "title": details_data.get("Title", clean_title),
                            "overview": details_data.get("Plot", ""),
                            "release_date": details_data.get("Year", str(year) if year else str(datetime.now().year)),
                            "genres": genres,
                            "poster_path": details_data.get("Poster") if details_data.get("Poster") != "N/A" else None,
                            "source": "OMDB",
                            "imdb_id": details_data.get("imdbID"),
                            "rating": details_data.get("Rated", "NR"),
                            "director": details_data.get("Director", ""),
                            "actors": details_data.get("Actors", "")
                        }
                        print(f"DEBUG: Found movie via OMDB search: {result['title']} ({result['release_date']})")
                        return result
            return None
                
        except Exception as e:
            print(f"Error searching OMDB: {e}")
            return None
    def get_wikipedia_page_info(self, page_title):
        """Get detailed information from a Wikipedia page"""
        try:
            print(f"DEBUG: Getting Wikipedia page info for: {page_title}")
            
            # Set proper headers for Wikipedia API
            headers = {
                'User-Agent': 'AkiraTV Collection Manager/1.0 (https://github.com/your-repo; your-email@example.com)'
            }
            
            # Get page content using Wikipedia API
            api_url = "https://en.wikipedia.org/w/api.php"
            
            # First, get the page content
            content_params = {
                "action": "query",
                "format": "json",
                "titles": page_title,
                "prop": "extracts|pageimages|categories|images",
                "exintro": True,
                "explaintext": True,
                "exsectionformat": "plain",
                "piprop": "original|name",
                "pilicense": "any",  # Allow any license for images
                "imlimit": 10  # Get up to 10 images
            }
            
            response = requests.get(api_url, params=content_params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            
            if not pages:
                print("DEBUG: No pages found in Wikipedia response")
                return None
            
            # Get the first (and usually only) page
            page_data = next(iter(pages.values()))
            
            if page_data.get("missing"):
                print("DEBUG: Wikipedia page is missing")
                return None
            
            # Extract information
            extract = page_data.get("extract", "")
            print(f"DEBUG: Wikipedia extract length: {len(extract)}")
            
            # Check if this is a soundtrack/score page - if so, reject it
            if any(skip in page_title.lower() for skip in ['soundtrack', 'film score', 'score album']):
                print(f"DEBUG: Rejecting soundtrack/score page: '{page_title}'")
                return None
            
            # Check extract content for soundtrack indicators
            extract_lower = extract.lower()
            if any(phrase in extract_lower for phrase in ['is the soundtrack', 'is the score', 'film score album', 'soundtrack album']):
                # Check if it's actually about a soundtrack vs the film itself
                if 'film of the same name' in extract_lower or 'motion picture' in extract_lower and 'score' in extract_lower:
                    print(f"DEBUG: Rejecting soundtrack page based on content: '{page_title}'")
                    return None
            
            # Try to extract year from the text - look for release year patterns
            year = datetime.now().year  # Default
            
            # First, check if the page title has a year (highest priority)
            title_year_match = re.search(r'\((\d{4})\s*film\)', page_title)
            if title_year_match:
                try:
                    title_year = int(title_year_match.group(1))
                    if 1900 <= title_year <= datetime.now().year:
                        year = title_year
                        print(f"DEBUG: Found year in title: {year}")
                except:
                    pass
            else:
                # Look for year patterns in the extract
                year_patterns = [
                    r'released in (\d{4})',
                    r'premiered in (\d{4})',
                    r'released on.*?(\d{4})',
                    r'(\d{4}) (?:Japanese |animated |anime )?film',
                    r'(\d{4}) (?:Japanese |animated |anime )?movie',
                    r'Release date.*?(\d{4})',
                    r'(\d{4}) release',
                    r'\b(19|20)\d{2}\b'  # Any 4-digit year as fallback
                ]
                
                for pattern in year_patterns:
                    year_match = re.search(pattern, extract, re.IGNORECASE)
                    if year_match:
                        try:
                            found_year = int(year_match.group(1))
                            if 1900 <= found_year <= datetime.now().year:  # Reasonable year range
                                year = found_year
                                print(f"DEBUG: Found year using pattern '{pattern}': {year}")
                                break
                        except:
                            continue
            
            # Try to extract genres from categories or text
            genres = []
            categories = page_data.get("categories", [])
            for cat in categories:
                cat_title = cat.get("title", "").lower()
                if "horror" in cat_title:
                    genres.append("Horror")
                elif "comedy" in cat_title:
                    genres.append("Comedy")
                elif "action" in cat_title:
                    genres.append("Action")
                elif "drama" in cat_title:
                    genres.append("Drama")
                elif "thriller" in cat_title:
                    genres.append("Thriller")
                elif "sci" in cat_title and "fi" in cat_title:
                    genres.append("Sci-Fi")
                elif "romance" in cat_title:
                    genres.append("Romance")
                elif "adventure" in cat_title:
                    genres.append("Adventure")
                elif "fantasy" in cat_title:
                    genres.append("Fantasy")
                elif "mystery" in cat_title:
                    genres.append("Mystery")
                elif "documentary" in cat_title:
                    genres.append("Documentary")
                elif "anime" in cat_title or "animation" in cat_title:
                    genres.append("Anime")
            
            # Remove duplicates
            genres = list(set(genres))
            print(f"DEBUG: Extracted genres: {genres}")
            
            # Get image URL - try multiple approaches
            image_url = None
            
            # First try pageimages
            pageimages = page_data.get("pageimages", {})
            if "original" in pageimages:
                image_url = pageimages["original"]["source"]
                print(f"DEBUG: Found pageimage URL: {image_url}")
            
            # If no pageimage, try to find a good image from the images list
            if not image_url:
                images = page_data.get("images", [])
                for img in images:
                    img_title = img.get("title", "").lower()
                    # Look for poster, cover, or promotional images
                    if any(keyword in img_title for keyword in ['poster', 'cover', 'promotional', '.jpg', '.png']):
                        # Get the actual image URL
                        img_info_params = {
                            "action": "query",
                            "format": "json",
                            "titles": img["title"],
                            "prop": "imageinfo",
                            "iiprop": "url"
                        }
                        
                        img_response = requests.get(api_url, params=img_info_params, headers=headers, timeout=10)
                        if img_response.status_code == 200:
                            img_data = img_response.json()
                            img_pages = img_data.get("query", {}).get("pages", {})
                            if img_pages:
                                img_page = next(iter(img_pages.values()))
                                imageinfo = img_page.get("imageinfo", [])
                                if imageinfo:
                                    image_url = imageinfo[0].get("url")
                                    print(f"DEBUG: Found image from images list: {image_url}")
                                    break
            
            # Create a summary (first paragraph or first 500 characters)
            summary = extract
            if len(summary) > 500:
                # Try to cut at sentence boundary
                sentences = summary.split('. ')
                summary = ""
                for sentence in sentences:
                    if len(summary + sentence) < 500:
                        summary += sentence + ". "
                    else:
                        break
                summary = summary.strip()
            
            result = {
                "title": page_data.get("title", ""),
                "overview": summary,
                "release_date": str(year),
                "genres": [{"name": genre} for genre in genres],
                "poster_path": image_url,
                "source": "Wikipedia"
            }
            
            print(f"DEBUG: Wikipedia result: {result['title']}, year: {year}, genres: {len(genres)}, has_image: {bool(image_url)}")
            return result
            
        except Exception as e:
            print(f"Error getting Wikipedia page info: {e}")
            return None
    def search_imdb_movie(self, title, year=None, search_hints=None):
        """Search for movie information on IMDb (web scraping)"""
        try:
            # Clean up the title for better search results
            clean_title = re.sub(r'\b(1080p|720p|2160p|4k|bluray|webrip|bdrip|dvdrip|x264|x265|h264|h265)\b', '', title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\b(fmp4|mp4|mkv|avi|mov|webm|remux|remastered|extended|uncut)\b', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\b(dd5\.1|aac|ac3|dts|flac)\b', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'[._\-]', ' ', clean_title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()

            # Search with clean title only (hints used for filtering, not in query)
            # Parse search hints to extract year and names
            hints_year, hints_names = self._parse_search_hints(search_hints)

            # Use year from hints if not provided directly
            search_year = year if year else hints_year

            print(f"DEBUG: Searching IMDb for: '{clean_title}'")
            if search_year:
                print(f"DEBUG: Using year: {search_year}")
            if hints_names:
                print(f"DEBUG: Will filter results by hints: {hints_names}")

            # Try the free movie_db API first (no registration needed)
            try:
                api_url = "http://theapache64.com/movie_db/search"
                params = {"keyword": clean_title}

                response = requests.get(api_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if not data.get("error", True) and data.get("data"):
                        movie_data = data["data"]
                        print(f"DEBUG: Found movie via free API: {movie_data.get('name')}")

                        # If we have search hints, verify the result contains the hints
                        if hints_names:
                            movie_name_lower = movie_data.get("name", "").lower()
                            plot_lower = movie_data.get("plot", "").lower()

                            hints_found = False
                            for hint in hints_names:
                                hint_lower = hint.lower()
                                if hint_lower in movie_name_lower or hint_lower in plot_lower:
                                    print(f"DEBUG: Search hint '{hint}' verified in result")
                                    hints_found = True
                                    break

                            if not hints_found:
                                print(f"DEBUG: Search hints not found in result, trying web scraping...")
                                # Fall through to web scraping for better matching
                                raise Exception("Hints not in result")

                        # Convert to our format
                        genres = movie_data.get("genre", "").split(",")
                        genres = [g.strip() for g in genres if g.strip()]
                        
                        # Extract year from API response if available
                        api_year = None
                        if movie_data.get("year"):
                            try:
                                api_year = int(movie_data.get("year"))
                            except:
                                pass
                        
                        # Use API year if available, otherwise use search year
                        release_year = api_year if api_year else (search_year if search_year else datetime.now().year)

                        print(f"DEBUG: Free API returned - Genres: {genres}, Year: {release_year}")

                        return {
                            "title": movie_data.get("name", clean_title),
                            "overview": movie_data.get("plot", ""),
                            "release_date": str(release_year),
                            "genres": [{"name": genre} for genre in genres],
                            "poster_path": movie_data.get("poster_url"),
                            "source": "IMDb (Free API)"
                        }
            except Exception as e:
                print(f"DEBUG: Free API failed: {e}")

            # Fallback to web scraping if API fails
            return self.search_imdb_web_scraping(clean_title, search_year, hints_names)

        except Exception as e:
            print(f"Error searching IMDb: {e}")
            return None

    def search_imdb_web_scraping(self, clean_title, year=None, search_hints=None):
        """Fallback IMDb web scraping method"""
        try:
            # Set proper headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Search IMDb using the find endpoint
            # Add year to search query if available for better results
            if year:
                search_query_text = f"{clean_title} {year}"
                print(f"DEBUG: Searching IMDb with year: '{search_query_text}'")
            else:
                search_query_text = clean_title
                print(f"DEBUG: Searching IMDb: '{search_query_text}'")
            
            search_query = urllib.parse.quote_plus(search_query_text)
            search_url = f"https://www.imdb.com/find/?q={search_query}&s=tt&ttype=ft&ref_=fn_ft"
            
            print(f"DEBUG: IMDb web scraping URL: {search_url}")
            
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            content = response.text
            print(f"DEBUG: Got response, length: {len(content)}")
            
            # Try multiple regex patterns for different IMDb layouts
            # Updated patterns for 2024+ IMDb structure
            patterns = [
                # Pattern 1: Look for result items with title links (most common)
                r'<a[^>]*href="(/title/tt\d+)[^"]*"[^>]*>(?:\s*<[^>]+>)*\s*([^<]+?)(?:\s*</[^>]+>)*\s*</a>',
                # Pattern 2: JSON data in scripts
                r'"@type":"Movie"[^}]*"url":"(/title/tt\d+)[^"]*"[^}]*"name":"([^"]+)"',
                # Pattern 3: Simple href pattern
                r'href="(/title/tt\d+)[^"]*"[^>]*>([^<]+)</a>',
                # Pattern 4: Look for ipc-title-link-wrapper (new IMDb class)
                r'ipc-title-link-wrapper[^>]*href="(/title/tt\d+)[^"]*"[^>]*>(?:[^<]*<[^>]+>)*([^<]+)',
                # Pattern 5: data-testid patterns
                r'data-testid="title-link"[^>]*href="(/title/tt\d+)[^"]*"[^>]*>([^<]+)',
            ]
            
            matches = []
            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                if matches:
                    print(f"DEBUG: Found {len(matches)} matches with pattern {i+1}")
                    # Clean up matches - ensure proper format
                    clean_matches = []
                    for match in matches:
                        if len(match) == 2:
                            url, title = match
                            # Clean up URL
                            if not url.startswith('/title/'):
                                url = f'/title/{url}/' if url.startswith('tt') else url
                            elif not url.endswith('/'):
                                url = url + '/'
                            # Clean up title - remove extra whitespace and HTML entities
                            title = re.sub(r'\s+', ' ', title.strip())
                            title = title.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
                            if title and len(title) > 1:  # Skip empty or single-char titles
                                clean_matches.append((url, title))
                    matches = clean_matches
                    if matches:
                        break
            
            if not matches:
                print("DEBUG: No IMDb results found in web scraping")
                return None
            
            # Find the best match
            best_match = None
            best_score = 0
            best_match_verified = False
            
            # Convert hints to list if needed and to lowercase
            if isinstance(search_hints, str):
                hints_list = [search_hints.lower()]
            elif search_hints:
                hints_list = [h.lower() for h in search_hints]
            else:
                hints_list = []
            
            # Normalize clean_title for better matching (remove all punctuation and extra spaces)
            clean_title_normalized = re.sub(r'[^\w\s]', '', clean_title.lower())
            clean_title_normalized = re.sub(r'\s+', ' ', clean_title_normalized).strip()
            
            for movie_url, movie_title in matches[:10]:  # Check first 10 results
                score = 0
                movie_title_clean = movie_title.strip()
                
                # Skip common non-movie results
                if any(skip in movie_title_clean.lower() for skip in ['tv series', 'tv mini', 'episode', 'video game']):
                    continue
                
                # Skip soundtrack/score albums
                if any(skip in movie_title_clean.lower() for skip in ['soundtrack', 'film score', 'score album', 'original motion picture score']):
                    print(f"DEBUG: Skipping soundtrack/score: '{movie_title_clean}'")
                    continue
                
                print(f"DEBUG: Evaluating: '{movie_title_clean}'")
                
                # Normalize movie title for comparison
                movie_title_normalized = re.sub(r'[^\w\s]', '', movie_title_clean.lower())
                movie_title_normalized = re.sub(r'\s+', ' ', movie_title_normalized).strip()
                
                # Create versions without spaces for acronym matching (e.g., "l a" -> "la")
                clean_title_no_spaces = clean_title_normalized.replace(' ', '')
                movie_title_no_spaces = movie_title_normalized.replace(' ', '')
                
                # Check for acronym/initial matches (e.g., "l a" matches "la")
                if clean_title_no_spaces == movie_title_no_spaces:
                    score += 250
                    print(f"DEBUG: Exact match (no spaces) bonus: +250")
                elif movie_title_no_spaces.startswith(clean_title_no_spaces):
                    score += 180
                    print(f"DEBUG: Title starts with (no spaces) bonus: +180")
                
                # Option D: Check if result starts with search title (ignoring punctuation)
                if movie_title_normalized.startswith(clean_title_normalized):
                    score += 150
                    print(f"DEBUG: Title starts with match bonus: +150")
                
                # Title similarity - check if normalized search term is in normalized result
                if clean_title_normalized in movie_title_normalized:
                    score += 50
                    print(f"DEBUG: Title match bonus: +50")
                
                # Word matching with normalization - but require ALL words to match for high score
                clean_words = clean_title_normalized.split()
                title_words = movie_title_normalized.split()
                clean_words_set = set(clean_words)
                title_words_set = set(title_words)
                matching_words = clean_words_set & title_words_set
                
                if matching_words:
                    word_score = len(matching_words) * 10
                    score += word_score
                    print(f"DEBUG: Word match bonus: +{word_score}")
                    
                    # Extra bonus if ALL words match (not just some)
                    if len(matching_words) == len(clean_words_set):
                        score += 50
                        print(f"DEBUG: All words match bonus: +50")
                
                # Exact or near-exact match (highest priority)
                if clean_title_normalized == movie_title_normalized:
                    score += 200
                    print(f"DEBUG: Exact match bonus: +200")
                
                # Check for hints in the title
                for hint in hints_list:
                    hint_normalized = re.sub(r'[^\w\s]', '', hint.lower())
                    if hint_normalized in movie_title_normalized:
                        score += 20
                        print(f"DEBUG: Hint '{hint}' found in title: +20")
                
                # Verify by checking cast/crew on movie page if we have hints
                verified = False
                if hints_list and score >= 100:
                    print(f"DEBUG: High score candidate, verifying cast/crew...")
                    verified = self._verify_movie_cast(movie_url, hints_list)
                    if verified:
                        score += 100  # Big bonus for verified match
                        print(f"DEBUG: Cast/crew verified! Bonus: +100")
                    else:
                        print(f"DEBUG: Cast/crew NOT verified")
                
                print(f"DEBUG: '{movie_title_clean}' scored {score} (verified: {verified})")
                
                if score > best_score or (score == best_score and verified):
                    best_score = score
                    best_match = movie_url
                    best_match_verified = verified
            
            if best_match and best_score >= 20:  # Minimum threshold to avoid bad matches
                print(f"DEBUG: Best match URL: {best_match} (score: {best_score}, verified: {best_match_verified})")
                return self.get_imdb_movie_info(best_match)
            else:
                print(f"DEBUG: No good matches found (best score: {best_score})")
                return None
            
        except Exception as e:
            print(f"Error in IMDb web scraping: {e}")
            return None

    def _verify_movie_cast(self, movie_url, hints_list):
        """Verify a movie by checking if hints (actor/director names) appear in cast/crew"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            full_url = f"https://www.imdb.com{movie_url}"
            response = requests.get(full_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            content = response.text.lower()
            
            # Check each hint (actor/director name)
            for hint in hints_list:
                hint_normalized = re.sub(r'[^\w\s]', '', hint.lower())
                hint_parts = hint_normalized.split()
                
                # Check if full name appears
                if hint_normalized in content:
                    print(f"DEBUG: Found hint '{hint}' in movie page")
                    return True
                
                # Also check for partial matches (first or last name)
                if len(hint_parts) >= 2:
                    for part in hint_parts:
                        if len(part) > 2 and part in content:  # Avoid matching "a", "the", etc.
                            # Check if it appears near "cast" or "director" keywords
                            cast_patterns = [
                                rf'{re.escape(part)}[^<>]*cast',
                                rf'star[^<>]*{re.escape(part)}',
                                rf'direct[^<>]*{re.escape(part)}',
                            ]
                            for pattern in cast_patterns:
                                if re.search(pattern, content, re.IGNORECASE):
                                    print(f"DEBUG: Found hint part '{part}' near cast/director keywords")
                                    return True
            
            return False
            
        except Exception as e:
            print(f"DEBUG: Error verifying cast: {e}")
            return False

    def get_imdb_movie_info(self, movie_url):
        """Get movie information from IMDb page"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            full_url = f"https://www.imdb.com{movie_url}"
            print(f"DEBUG: Getting IMDb movie info from: {full_url}")
            
            response = requests.get(full_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            content = response.text
            
            # Extract title - try multiple patterns
            title = ""
            original_title = ""
            
            # Pattern 1: Look for the English/AKA title in the page
            # IMDb often shows "Original title: <original>" and the main title is the English one
            aka_match = re.search(r'original title[:\s]+([^<]+)', content, re.IGNORECASE)
            if aka_match:
                original_title = aka_match.group(1).strip()
            
            # Pattern 2: Look for title in JSON-LD - this usually has the English title
            json_ld_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', content, re.DOTALL | re.IGNORECASE)
            if json_ld_match:
                json_content = json_ld_match.group(1)
                # Try to find name in JSON
                name_match = re.search(r'"name"\s*:\s*"([^"]+)"', json_content)
                if name_match:
                    title = name_match.group(1).strip()
                    # Unescape unicode
                    title = title.encode('utf-8').decode('unicode-escape')
            
            # Pattern 3: h1 tag - often contains the English title
            if not title:
                title_match = re.search(r'<h1[^>]*>(?:\s*<[^>]+>)*\s*([^<]+?)(?:\s*</[^>]+>)*\s*</h1>', content, re.IGNORECASE | re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()
            
            # Pattern 4: Look for meta title tag - usually has English title
            if not title:
                meta_title_match = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', content, re.IGNORECASE)
                if meta_title_match:
                    title = meta_title_match.group(1).strip()
                    # Remove " - IMDb" suffix if present
                    title = re.sub(r'\s*-\s*IMDb$', '', title, flags=re.IGNORECASE)
            
            # Pattern 5: Look for alternativeHeadline which often has English title
            if not title:
                alt_title_match = re.search(r'"alternativeHeadline"\s*:\s*"([^"]+)"', content)
                if alt_title_match:
                    title = alt_title_match.group(1).strip()
            
            # Extract year - improved method
            year = datetime.now().year
            
            # Try JSON-LD first (most reliable)
            if json_ld_match:
                json_content = json_ld_match.group(1)
                # Look for release date in JSON-LD
                date_match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', json_content)
                if date_match:
                    try:
                        release_date = date_match.group(1).strip()
                        if release_date:
                            # Extract year from date string (format: YYYY-MM-DD or YYYY)
                            if '-' in release_date:
                                year = int(release_date.split('-')[0])
                            else:
                                year = int(release_date)
                            print(f"DEBUG: Found year from JSON-LD: {year}")
                    except:
                        pass
            
            # Try data-testid patterns for release year
            if year == datetime.now().year:
                year_patterns = [
                    r'<span[^>]*data-testid="title-year"[^>]*>(\d{4})</span>',
                    r'<a[^>]*href="/title/tt\d+/releaseinfo"[^>]*>(\d{4})</a>',
                    r'release year[^>]*(\d{4})',
                    r'\b(19|20)\d{2}\b'  # Fallback to any 4-digit year
                ]
                
                for pattern in year_patterns:
                    year_match = re.search(pattern, content, re.IGNORECASE)
                    if year_match:
                        try:
                            year_candidate = int(year_match.group(1))
                            if 1900 <= year_candidate <= datetime.now().year + 5:  # Allow for future releases
                                year = year_candidate
                                print(f"DEBUG: Found year using pattern '{pattern}': {year}")
                                break
                        except:
                            continue
            
            # Extract plot/description
            plot_patterns = [
                r'<span[^>]*data-testid="plot-xl"[^>]*>([^<]+)</span>',
                r'<span[^>]*data-testid="plot-l"[^>]*>([^<]+)</span>',
                r'<span[^>]*data-testid="plot"[^>]*>([^<]+)</span>',
            ]
            
            plot = ""
            for pattern in plot_patterns:
                plot_match = re.search(pattern, content, re.DOTALL)
                if plot_match:
                    plot = plot_match.group(1).strip()
                    break
            
            # Extract genres - updated patterns for current IMDb structure
            genres = []
            
            # Try JSON-LD genres first (most reliable)
            if json_ld_match:
                json_content = json_ld_match.group(1)
                # Look for genres in JSON-LD
                genre_match = re.search(r'"genre"\s*:\s*\[([^\]]+)\]', json_content)
                if genre_match:
                    genre_str = genre_match.group(1)
                    # Extract genre names from JSON array
                    genre_names = re.findall(r'"([^"]+)"', genre_str)
                    if genre_names:
                        genres = [g.strip() for g in genre_names if g.strip()]
                        print(f"DEBUG: Found genres from JSON-LD: {genres}")
            
            # If no genres from JSON-LD, try other patterns
            if not genres:
                genre_patterns = [
                    # New IMDb genre patterns
                    r'<a[^>]*href="/search/title\?genres=([^"&]+)"[^>]*>([^<]+)</a>',
                    r'<span[^>]*class="ipc-metadata-list-item__list-content-item"[^>]*>([^<]+)</span>',
                    r'<a[^>]*href="/genre/[^"]+"[^>]*>([^<]+)</a>'
                ]
                
                for pattern in genre_patterns:
                    genre_matches = re.findall(pattern, content)
                    if genre_matches:
                        # Extract genre names from matches
                        extracted_genres = []
                        for match in genre_matches:
                            if isinstance(match, tuple):
                                genre = match[1].strip()
                            else:
                                genre = match.strip()
                            
                            # Filter out non-genre text and duplicates
                            if genre and genre not in extracted_genres and len(genre) < 50:
                                # Exclude common non-genre terms
                                if not any(exclude in genre.lower() for exclude in ['see more', 'all', 'genres', 'release', 'year']):
                                    extracted_genres.append(genre)
                        
                        if extracted_genres:
                            genres = extracted_genres[:5]  # Limit to 5 genres
                            print(f"DEBUG: Found genres using pattern '{pattern}': {genres}")
                            break
            
            # Try to find poster image - multiple patterns
            poster_url = None
            
            # Pattern 1: Look for poster in JSON-LD
            if not poster_url and json_ld_match:
                json_content = json_ld_match.group(1)
                json_image_match = re.search(r'"image"\s*:\s*"([^"]+)"', json_content)
                if json_image_match:
                    poster_url = json_image_match.group(1).strip()
            
            # Pattern 2: Look for og:image meta tag
            if not poster_url:
                og_image_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', content, re.IGNORECASE)
                if og_image_match:
                    poster_url = og_image_match.group(1).strip()
            
            # Pattern 3: Look for poster in img tags with poster-related alt text
            if not poster_url:
                poster_pattern = r'<img[^>]*src="([^"]*\.jpg[^"]*)"[^>]*alt="[^"]*poster[^"]*"'
                poster_match = re.search(poster_pattern, content, re.IGNORECASE)
                if poster_match:
                    poster_url = poster_match.group(1)
            
            # Pattern 4: Look for any large image that might be the poster
            if not poster_url:
                # Look for images with specific IMDb poster URL patterns
                poster_pattern = r'https://m\.media-amazon\.com/images/M/[^"\s]+\.jpg'
                poster_matches = re.findall(poster_pattern, content)
                if poster_matches:
                    # Filter for larger images (usually contain UX or similar in path)
                    for match in poster_matches:
                        if 'UX' in match or 'UY' in match:
                            poster_url = match
                            break
                    # If no large image found, use the first one
                    if not poster_url:
                        poster_url = poster_matches[0]
            
            print(f"DEBUG: IMDb movie info extracted - Title: {title}, Year: {year}, Genres: {genres}, Poster: {bool(poster_url)}")
            
            return {
                "title": title,
                "overview": plot,
                "release_date": str(year),
                "genres": [{"name": genre} for genre in genres],
                "poster_path": poster_url,
                "source": "IMDb"
            }
            
        except Exception as e:
            print(f"Error getting IMDb movie info: {e}")
            return None
    def create_fallback_metadata(self, title, year=None, original_title=None, video_path=None, language="english"):
        """Create basic metadata when online sources fail"""
        print(f"DEBUG: Creating fallback metadata for: {title} in {language}")
        
        # Clean up the title
        clean_title = re.sub(r'\b(1080p|720p|2160p|4k|bluray|webrip|bdrip|dvdrip|x264|x265|h264|h265)\b', '', title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\b(fmp4|mp4|mkv|avi|mov|webm|remux|remastered|extended|uncut)\b', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\b(dd5\.1|aac|ac3|dts|flac)\b', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'[._\-]', ' ', clean_title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        # Try to extract year from filename if not provided
        if not year and video_path:
            year_match = re.search(r'\b(19|20)\d{2}\b', str(video_path))
            if year_match:
                year = int(year_match.group())
        
        if not year:
            year = datetime.now().year
        
        # Try to determine genre from title keywords
        genres = []
        title_lower = clean_title.lower()
        
        # Genre detection based on keywords
        if any(word in title_lower for word in ['horror', 'nightmare', 'evil', 'dead', 'zombie', 'vampire', 'ghost', 'demon', 'terror', 'scream', 'friday', 'halloween']):
            genres.append("Horror")
        if any(word in title_lower for word in ['action', 'fight', 'war', 'battle', 'combat', 'mission', 'force', 'strike', 'assault']):
            genres.append("Action")
        if any(word in title_lower for word in ['comedy', 'funny', 'laugh', 'humor', 'comic']):
            genres.append("Comedy")
        if any(word in title_lower for word in ['love', 'romance', 'romantic', 'heart', 'wedding', 'kiss']):
            genres.append("Romance")
        if any(word in title_lower for word in ['sci-fi', 'science', 'space', 'alien', 'future', 'robot', 'cyber', 'matrix', 'star', 'galaxy']):
            genres.append("Sci-Fi")
        if any(word in title_lower for word in ['adventure', 'quest', 'journey', 'treasure', 'explorer', 'expedition']):
            genres.append("Adventure")
        if any(word in title_lower for word in ['thriller', 'suspense', 'mystery', 'detective', 'crime', 'murder', 'killer']):
            genres.append("Thriller")
        if any(word in title_lower for word in ['drama', 'life', 'story', 'family', 'emotional']):
            genres.append("Drama")
        if any(word in title_lower for word in ['fantasy', 'magic', 'wizard', 'dragon', 'fairy', 'legend', 'myth']):
            genres.append("Fantasy")
        if any(word in title_lower for word in ['anime', 'manga', 'japanese', 'naruto', 'dragon ball', 'pokemon']):
            genres.append("Anime")
        
        # If no genres detected, add a generic one
        if not genres:
            genres = ["Drama"]
        
        # Get description from known movies database
        description = self.get_known_movie_description(clean_title, year, language)
        
        return {
            "title": original_title or clean_title,
            "overview": description,
            "release_date": str(year),
            "genres": [{"name": genre} for genre in genres],
            "poster_path": None,
            "source": "Fallback"
        }
    def get_known_movie_title(self, title, language="english"):
        """Get translated title for well-known movies"""
        title_lower = title.lower()
        
        # Return original title (English is sufficient)
        return title

    def get_known_movie_description(self, title, year, language="english"):
        """Get description for well-known movies"""
        title_lower = title.lower()
        
        # English descriptions for popular movies
        known_movies_en = {
            "terminator": f"A {year} science fiction action film about a cyborg assassin sent from the future.",
            "alien": f"A {year} science fiction horror film about a deadly extraterrestrial creature in space.",
            "predator": f"A {year} action science fiction film about an alien hunter in the jungle.",
            "matrix": f"A {year} science fiction action film about virtual reality and the fight for freedom.",
            "blade runner": f"A {year} science fiction film about an android hunter in a dystopian future.",
            "star wars": f"A {year} space opera about the battle between good and evil in a galaxy far, far away.",
            "indiana jones": f"A {year} adventure action film about an archaeologist and his dangerous missions.",
            "die hard": f"A {year} action film about a cop fighting terrorists.",
            "rambo": f"A {year} action war film about a Vietnam veteran and his missions.",
            "rocky": f"A {year} sports drama about a boxer and his path to glory.",
            "godfather": f"A {year} crime drama about an Italian-American mafia family.",
            "scarface": f"A {year} crime drama about the rise and fall of a drug lord.",
            "goodfellas": f"A {year} crime drama about life in the mafia.",
            "casino": f"A {year} crime drama about corruption and power in Las Vegas.",
            "pulp fiction": f"A {year} crime drama with intertwined stories from the underworld.",
            "kill bill": f"A {year} action film about revenge and martial arts.",
            "batman": f"A {year} superhero film about the Dark Knight of Gotham City.",
            "superman": f"A {year} superhero film about the Man of Steel.",
            "spider-man": f"A {year} superhero film about the web-slinger.",
            "x-men": f"A {year} superhero film about mutants with supernatural abilities.",
            "avengers": f"A {year} superhero film about a team of superheroes.",
            "iron man": f"A {year} superhero film about a genius inventor in armored suit.",
            "captain america": f"A {year} superhero film about the super-soldier from World War II.",
            "thor": f"A {year} superhero film about the Norse god of thunder.",
            "hulk": f"A {year} superhero film about a scientist who transforms into a green giant.",
            "transformers": f"A {year} science fiction action film about robots that transform into cars.",
            "fast and furious": f"A {year} action film about street racing and criminal operations.",
            "mission impossible": f"A {year} action spy film about secret agents and dangerous missions.",
            "james bond": f"A {year} spy action film about the British secret agent 007.",
            "john wick": f"A {year} action film about a professional assassin in the underworld.",
            "taken": f"A {year} action thriller about a father searching for his kidnapped daughter.",
            "bourne": f"A {year} spy thriller about an agent with amnesia.",
            "mad max": f"A {year} post-apocalyptic action film in a desert world.",
            "expendables": f"A {year} action film about a team of mercenaries.",
            "lethal weapon": f"A {year} action comedy about two police partners.",
            "beverly hills cop": f"A {year} action comedy about a detective in Beverly Hills.",
            "rush hour": f"A {year} action comedy about a police duo.",
            "men in black": f"A {year} science fiction comedy about secret agents and aliens.",
            "ghostbusters": f"A {year} comedy about ghost hunters in New York.",
            "back to the future": f"A {year} science fiction comedy about time travel.",
            "jurassic park": f"A {year} science fiction thriller about resurrected dinosaurs.",
            "jaws": f"A {year} thriller about a giant great white shark.",
            "the shining": f"A {year} psychological horror about madness in an isolated hotel.",
            "halloween": f"A {year} horror film about the serial killer Michael Myers.",
            "friday the 13th": f"A {year} horror film about murders at Camp Crystal Lake.",
            "nightmare on elm street": f"A {year} horror film about Freddy Krueger and nightmares.",
            "scream": f"A {year} horror film about a serial killer with a mask.",
            "saw": f"A {year} horror thriller about sadistic life-and-death games.",
            "final destination": f"A {year} horror film about death and its plans.",
            "the ring": f"A {year} horror film about a cursed video.",
            "the grudge": f"A {year} horror film about a cursed house.",
            "paranormal activity": f"A {year} horror film about supernatural phenomena in a home.",
            "conjuring": f"A {year} horror film about demonologists and ghosts.",
            "insidious": f"A {year} horror film about astral projection and demons.",
            "sinister": f"A {year} horror film about ancient evil and family tragedies.",
            "it": f"A {year} horror film about the clown Pennywise and his terror.",
            "the exorcist": f"A {year} horror film about demonic possession.",
            "poltergeist": f"A {year} horror film about ghosts in a family home.",
            "amityville": f"A {year} horror film about a house with a dark past.",
            "child's play": f"A {year} horror film about the killer doll Chucky.",
            "annabelle": f"A {year} horror film about a cursed doll.",
            "the nun": f"A {year} horror film about a demonic nun.",
            "lights out": f"A {year} horror film about a creature that lives in darkness.",
            "don't breathe": f"A {year} thriller about a blind man and thieves in his house.",
            "get out": f"A {year} psychological thriller about racism and hypnosis.",
            "us": f"A {year} horror thriller about a family and their doppelgangers.",
            "hereditary": f"A {year} horror film about family secrets and occultism.",
            "midsommar": f"A {year} horror film about a Scandinavian festival and rituals.",
            "the witch": f"A {year} horror film about a witch in colonial America.",
            "the babadook": f"A {year} psychological horror about a mother, child, and monster.",
            "it follows": f"A {year} horror film about a curse that follows you.",
            "a quiet place": f"A {year} horror thriller about a family in a world of silence.",
            "bird box": f"A {year} post-apocalyptic thriller about a world where you can't look.",
            "the platform": f"A {year} science fiction thriller about social hierarchy.",
            "parasite": f"A {year} thriller drama about class differences in Korea.",
            "joker": f"A {year} psychological drama about the origin of the villain Joker.",
            "braveheart": f"A {year} historical drama about William Wallace and Scottish freedom.",
            "gladiator": f"A {year} historical drama about a Roman general turned gladiator.",
            "troy": f"A {year} epic drama about the Trojan War.",
            "300": f"A {year} action film about the 300 Spartans at Thermopylae.",
            "alexander": f"A {year} biographical drama about Alexander the Great.",
            "kingdom of heaven": f"A {year} historical drama about the Crusades.",
            "the last samurai": f"A {year} historical drama about an American officer in Japan.",
            "apocalypto": f"A {year} historical drama about Mayan civilization.",
            "anime": f"A {year} Japanese animated film.",
            "manga": f"A {year} film based on Japanese manga.",
            "dragon ball": f"A {year} animated film from the Dragon Ball series.",
            "naruto": f"A {year} animated film from the Naruto series.",
            "one piece": f"A {year} animated film from the One Piece series.",
            "attack on titan": f"A {year} animated film about titans.",
            "death note": f"A {year} thriller about a notebook of death.",
            "fullmetal alchemist": f"A {year} fantasy film about alchemy.",
            "ghost in the shell": f"A {year} science fiction film about cyborgs.",
            "akira": f"A {year} science fiction animated film.",
            "spirited away": f"A {year} fantasy animated film by Hayao Miyazaki.",
            "princess mononoke": f"A {year} fantasy animated film about nature.",
            "my neighbor totoro": f"A {year} family animated film about forest spirits.",
            "castle in the sky": f"A {year} adventure animated film.",
            "howl's moving castle": f"A {year} fantasy animated film about magic.",
            "your name": f"A {year} romantic animated film about body swapping.",
            "weathering with you": f"A {year} romantic animated film about weather.",
            "demon slayer": f"A {year} animated action about demon hunters.",
            "jujutsu kaisen": f"A {year} animated action about curses.",
            "my hero academia": f"A {year} superhero animated film.",
            "one punch man": f"A {year} superhero animated comedy.",
            "hunter x hunter": f"A {year} adventure animated film.",
            "bleach": f"A {year} supernatural animated action.",
            "tokyo ghoul": f"A {year} horror animated film about ghouls.",
            "parasyte": f"A {year} horror science fiction animated film.",
            "cowboy bebop": f"A {year} space western animated film.",
            "samurai champloo": f"A {year} historical animated film about samurai.",
            "vampire hunter d": f"A {year} horror animated film about a vampire hunter.",
            "neon genesis evangelion": f"A {year} science fiction animated film about mecha."
        }
        
        # Check for matches in English database
        for key, description in known_movies_en.items():
            if key in title_lower:
                return description
        
        # Generic fallback description
            return f"A {year} film."
    def download_poster(self, poster_path, movie_title):
        """Download movie poster from TMDB"""
        if not poster_path:
            return None
        
        try:
            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', movie_title)
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            filename = f"{safe_title.lower()}.jpg"
            
            poster_file_path = self.covers_dir / filename
            
            # Check if cover already exists
            if poster_file_path.exists():
                print(f"DEBUG: Cover already exists: {poster_file_path}")
                return f"user/covers/{filename}"
            
            # Handle different poster path formats
            if poster_path.startswith('http'):
                poster_url = poster_path
            else:
                poster_url = f"{self.tmdb_image_base_url}{poster_path}"
            
            print(f"DEBUG: Downloading poster from: {poster_url}")
            
            response = requests.get(poster_url, timeout=10)
            response.raise_for_status()
            
            with open(poster_file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"DEBUG: Poster saved to: {poster_file_path}")
            # Return relative path for collection storage
            return f"user/covers/{filename}"
            
        except Exception as e:
            print(f"Error downloading poster: {e}")
            return None

    def download_wikipedia_image(self, image_url, movie_title):
        """Download image from Wikipedia"""
        if not image_url:
            return None
        
        try:
            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', movie_title)
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            
            # Get file extension from URL
            ext = '.jpg'
            if '.png' in image_url.lower():
                ext = '.png'
            elif '.gif' in image_url.lower():
                ext = '.gif'
            
            filename = f"{safe_title.lower()}{ext}"
            image_file_path = self.covers_dir / filename
            
            # Check if cover already exists
            if image_file_path.exists():
                print(f"DEBUG: Cover already exists: {image_file_path}")
                return f"user/covers/{filename}"
            
            print(f"DEBUG: Downloading Wikipedia image from: {image_url}")
            
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            with open(image_file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"DEBUG: Wikipedia image saved to: {image_file_path}")
            # Return relative path for collection storage
            return f"user/covers/{filename}"
            
        except Exception as e:
            print(f"Error downloading Wikipedia image: {e}")
            return None

    def download_imdb_image(self, image_url, movie_title):
        """Download image from IMDb or free API"""
        if not image_url:
            return None
        
        try:
            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', movie_title)
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            
            # Get file extension from URL or content type
            ext = '.jpg'
            if '.png' in image_url.lower():
                ext = '.png'
            elif '.gif' in image_url.lower():
                ext = '.gif'
            
            filename = f"{safe_title.lower()}{ext}"
            image_file_path = self.covers_dir / filename
            
            # Check if cover already exists
            if image_file_path.exists():
                print(f"DEBUG: Cover already exists: {image_file_path}")
                return f"user/covers/{filename}"
            
            print(f"DEBUG: Downloading IMDb image from: {image_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Check content type for extension
            content_type = response.headers.get('content-type', '')
            if 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            
            with open(image_file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"DEBUG: IMDb image saved to: {image_file_path}")
            # Return relative path for collection storage
            return f"user/covers/{filename}"
            
        except Exception as e:
            print(f"Error downloading IMDb image: {e}")
            return None
    
    def download_omdb_image(self, image_url, movie_title):
        """Download image from OMDB"""
        if not image_url:
            return None
        
        try:
            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', movie_title)
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            
            # Get file extension from URL or content type
            ext = '.jpg'
            if '.png' in image_url.lower():
                ext = '.png'
            elif '.gif' in image_url.lower():
                ext = '.gif'
            
            filename = f"{safe_title.lower()}{ext}"
            image_file_path = self.covers_dir / filename
            
            # Check if cover already exists
            if image_file_path.exists():
                print(f"DEBUG: Cover already exists: {image_file_path}")
                return f"user/covers/{filename}"
            
            print(f"DEBUG: Downloading OMDB image from: {image_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Check content type for extension
            content_type = response.headers.get('content-type', '')
            if 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            
            with open(image_file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"DEBUG: OMDB image saved to: {image_file_path}")
            # Return relative path for collection storage
            return f"user/covers/{filename}"
            
        except Exception as e:
            print(f"Error downloading OMDB image: {e}")
            return None