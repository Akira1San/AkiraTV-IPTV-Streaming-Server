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

    def search_tmdb_movie(self, title, year=None):
        """Search for movie on TMDB"""
        if not self.tmdb_api_key:
            return None
        
        try:
            # Clean up the title for better search results
            clean_title = re.sub(r'\b(1080p|720p|2160p|4k|bluray|webrip|bdrip|dvdrip|x264|x265|h264|h265)\b', '', title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\b(fmp4|mp4|mkv|avi|mov|webm|remux|remastered|extended|uncut)\b', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'[._\-]', ' ', clean_title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            
            # Search for the movie
            search_url = f"{self.tmdb_base_url}/search/movie"
            params = {
                "api_key": self.tmdb_api_key,
                "query": clean_title
            }
            
            if year:
                params["year"] = year
            
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if results:
                # Return the first (most relevant) result
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
    def search_wikipedia_movie(self, title, year=None):
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
            
            # Try different search variations with better logic
            search_terms = []
            
            if year:
                # Most specific searches first
                search_terms.extend([
                    f"{clean_title} ({year} film)",
                    f"{clean_title} {year} film",
                    f"{clean_title} ({year})",
                ])
            
            # General searches
            search_terms.extend([
                f"{clean_title} film",
                f"{clean_title} movie", 
                clean_title
            ])
            
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
                    
                    for result_title in titles:
                        score = 0
                        result_lower = result_title.lower()
                        
                        # Scoring system for better matches
                        if year and f"({year}" in result_title:
                            score += 100  # Exact year match is highest priority
                        elif year and str(year) in result_title:
                            score += 50   # Year mentioned somewhere
                        
                        if "film)" in result_lower:
                            score += 30   # Proper film disambiguation
                        elif "film" in result_lower:
                            score += 20   # Contains film
                        elif "movie" in result_lower:
                            score += 15   # Contains movie
                        
                        # Exact title match bonus
                        if clean_title.lower() in result_lower:
                            score += 25
                        
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
    def search_imdb_movie(self, title, year=None, language="english"):
        """Search for movie information on IMDb (web scraping)"""
        try:
            # Clean up the title for better search results
            clean_title = re.sub(r'\b(1080p|720p|2160p|4k|bluray|webrip|bdrip|dvdrip|x264|x265|h264|h265)\b', '', title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\b(fmp4|mp4|mkv|avi|mov|webm|remux|remastered|extended|uncut)\b', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\b(dd5\.1|aac|ac3|dts|flac)\b', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'[._\-]', ' ', clean_title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            
            print(f"DEBUG: Searching IMDb for: '{clean_title}'")
            
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
                        
                        # Convert to our format
                        genres = movie_data.get("genre", "").split(",")
                        genres = [g.strip() for g in genres if g.strip()]
                        
                        return {
                            "title": movie_data.get("name", clean_title),
                            "overview": movie_data.get("plot", ""),
                            "release_date": str(year) if year else str(datetime.now().year),
                            "genres": [{"name": genre} for genre in genres],
                            "poster_path": movie_data.get("poster_url"),
                            "source": "IMDb (Free API)"
                        }
            except Exception as e:
                print(f"DEBUG: Free API failed: {e}")
            
            # Fallback to web scraping if API fails
            return self.search_imdb_web_scraping(clean_title, year, language)
            
        except Exception as e:
            print(f"Error searching IMDb: {e}")
            return None

    def search_imdb_web_scraping(self, clean_title, year=None, language="english"):
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
            search_query = urllib.parse.quote_plus(clean_title)
            search_url = f"https://www.imdb.com/find/?q={search_query}&s=tt&ttype=ft&ref_=fn_ft"
            
            print(f"DEBUG: Trying IMDb web scraping: {search_url}")
            
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
                print("DEBUG: No IMDb results found in web scraping, trying fallback")
                # Create basic metadata from title as fallback
                return self.create_fallback_metadata(clean_title, year, language=language)
            
            # Find the best match
            best_match = None
            best_score = 0
            
            for movie_url, movie_title in matches[:10]:  # Check first 10 results
                score = 0
                movie_title_clean = movie_title.strip()
                
                # Skip common non-movie results
                if any(skip in movie_title_clean.lower() for skip in ['tv series', 'tv mini', 'episode', 'video game']):
                    continue
                
                print(f"DEBUG: Evaluating: '{movie_title_clean}'")
                
                # Year matching - check if year appears in title
                if year:
                    if str(year) in movie_title_clean:
                        score += 100
                        print(f"DEBUG: Year match bonus: +100")
                
                # Title similarity - check if search term is in result
                clean_title_lower = clean_title.lower()
                movie_title_lower = movie_title_clean.lower()
                
                if clean_title_lower in movie_title_lower:
                    score += 50
                    print(f"DEBUG: Title match bonus: +50")
                
                # Word matching - count matching words
                clean_words = set(clean_title_lower.split())
                title_words = set(movie_title_lower.split())
                matching_words = clean_words & title_words
                if matching_words:
                    score += len(matching_words) * 10
                    print(f"DEBUG: Word match bonus: +{len(matching_words) * 10}")
                
                # Exact match
                if clean_title_lower == movie_title_lower:
                    score += 75
                    print(f"DEBUG: Exact match bonus: +75")
                
                print(f"DEBUG: '{movie_title_clean}' scored {score}")
                
                if score > best_score:
                    best_score = score
                    best_match = movie_url
            
            if best_match and best_score >= 20:  # Minimum threshold to avoid bad matches
                print(f"DEBUG: Best match URL: {best_match} (score: {best_score})")
                return self.get_imdb_movie_info(best_match)
            else:
                print(f"DEBUG: No good matches found (best score: {best_score}), using fallback")
                return self.create_fallback_metadata(clean_title, year, language=language)
            
        except Exception as e:
            print(f"Error in IMDb web scraping: {e}")
            return self.create_fallback_metadata(clean_title, year, language=language)

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
            
            # Extract year
            year_match = re.search(r'<span[^>]*>(\d{4})</span>', content)
            year = int(year_match.group(1)) if year_match else datetime.now().year
            
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
            
            # Extract genres
            genre_pattern = r'<a[^>]*href="/search/title/\?genres=([^"]+)"[^>]*>([^<]+)</a>'
            genre_matches = re.findall(genre_pattern, content)
            genres = [match[1] for match in genre_matches[:5]]  # Limit to 5 genres
            
            # Try to find poster image - multiple patterns
            poster_url = None
            
            # Pattern 1: Look for poster in JSON-LD
            if not poster_url:
                json_image_match = re.search(r'"image"\s*:\s*"([^"]+)"', content)
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
    def get_known_movie_description(self, title, year, language="english"):
        """Get description for well-known movies"""
        title_lower = title.lower()
        
        # Bulgarian descriptions for popular movies
        if language == "bulgarian":
            known_movies_bg = {
                "terminator": f"Научнофантастичен екшън филм от {year} година за киборг убиец, изпратен от бъдещето.",
                "alien": f"Научнофантастичен хорър филм от {year} година за смъртоносно извземно създание в космоса.",
                "predator": f"Екшън научнофантастичен филм от {year} година за извънземен ловец в джунглата.",
                "matrix": f"Научнофантастичен екшън филм от {year} година за виртуална реалност и борбата за свободата.",
                "blade runner": f"Научнофантастичен филм от {year} година за ловец на андроиди в дистопично бъдеще.",
                "star wars": f"Космическа опера от {year} година за борбата между добро и зло в далечна галактика.",
                "indiana jones": f"Приключенски екшън филм от {year} година за археолог и неговите опасни мисии.",
                "die hard": f"Екшън филм от {year} година за полицай, който се бори срещу терористи.",
                "rambo": f"Екшън военен филм от {year} година за ветеран от Виетнам и неговите мисии.",
                "rocky": f"Спортна драма от {year} година за боксьор и неговия път към славата.",
                "godfather": f"Криминална драма от {year} година за италианско-американско мафиотско семейство.",
                "scarface": f"Криминална драма от {year} година за възхода и падението на наркобарон.",
                "goodfellas": f"Криминална драма от {year} година за живота в мафията.",
                "casino": f"Криминална драма от {year} година за корупция и власт в Лас Вегас.",
                "pulp fiction": f"Криминална драма от {year} година с преплетени истории от подземния свят.",
                "kill bill": f"Екшън филм от {year} година за отмъщение и бойни изкуства.",
                "batman": f"Супергеройски филм от {year} година за Тъмния рицар на Готъм Сити.",
                "superman": f"Супергеройски филм от {year} година за Човека от стомана.",
                "spider-man": f"Супергеройски филм от {year} година за паякочовека.",
                "x-men": f"Супергеройски филм от {year} година за мутанти с свръхестествени способности.",
                "avengers": f"Супергеройски филм от {year} година за отбор от супергерои.",
                "iron man": f"Супергеройски филм от {year} година за гениален изобретател в бронирана броня.",
                "captain america": f"Супергеройски филм от {year} година за супер-войника от Втората световна война.",
                "thor": f"Супергеройски филм от {year} година за скандинавския бог на гръмотевиците.",
                "hulk": f"Супергеройски филм от {year} година за учен, който се превръща в зелен гигант.",
                "transformers": f"Научнофантастичен екшън филм от {year} година за роботи, които се превръщат в коли.",
                "fast and furious": f"Екшън филм от {year} година за улични състезания и криминални операции.",
                "mission impossible": f"Екшън шпионски филм от {year} година за тайни агенти и опасни мисии.",
                "james bond": f"Шпионски екшън филм от {year} година за британския таен агент 007.",
                "john wick": f"Екшън филм от {year} година за професионален убиец в подземния свят.",
                "taken": f"Екшън трилър от {year} година за баща, който търси отвлечената си дъщеря.",
                "bourne": f"Шпионски трилър от {year} година за агент с амнезия.",
                "mad max": f"Постапокалиптичен екшън филм от {year} година в пустинен свят.",
                "expendables": f"Екшън филм от {year} година за отбор от наемници.",
                "lethal weapon": f"Екшън комедия от {year} година за двама полицейски партньори.",
                "beverly hills cop": f"Екшън комедия от {year} година за детектив в Бевърли Хилс.",
                "rush hour": f"Екшън комедия от {year} година за полицейски дует.",
                "men in black": f"Научнофантастична комедия от {year} година за тайни агенти и извънземни.",
                "ghostbusters": f"Комедия от {year} година за ловци на духове в Ню Йорк.",
                "back to the future": f"Научнофантастична комедия от {year} година за пътуване във времето.",
                "jurassic park": f"Научнофантастичен трилър от {year} година за възкресени динозаври.",
                "jaws": f"Трилър от {year} година за гигантска бяла акула.",
                "the shining": f"Психологически хорър от {year} година за лудост в изолиран хотел.",
                "halloween": f"Хорър филм от {year} година за серийния убиец Майкъл Майърс.",
                "friday the 13th": f"Хорър филм от {year} година за убийствата в лагер Кристъл Лейк.",
                "nightmare on elm street": f"Хорър филм от {year} година за Фреди Крюгер и кошмарите.",
                "scream": f"Хорър филм от {year} година за серийен убиец с маска.",
                "saw": f"Хорър трилър от {year} година за садистични игри на живот и смърт.",
                "final destination": f"Хорър филм от {year} година за смъртта и нейните планове.",
                "the ring": f"Хорър филм от {year} година за проклето видео.",
                "the grudge": f"Хорър филм от {year} година за проклет дом.",
                "paranormal activity": f"Хорър филм от {year} година за свръхестествени явления в дома.",
                "conjuring": f"Хорър филм от {year} година за демонолози и призраци.",
                "insidious": f"Хорър филм от {year} година за астрална проекция и демони.",
                "sinister": f"Хорър филм от {year} година за древно зло и семейни трагедии.",
                "it": f"Хорър филм от {year} година за клоуна Пенивайз и неговия терор.",
                "the exorcist": f"Хорър филм от {year} година за демонично обладаване.",
                "poltergeist": f"Хорър филм от {year} година за призраци в семеен дом.",
                "amityville": f"Хорър филм от {year} година за дом с тъмно минало.",
                "child's play": f"Хорър филм от {year} година за убийствена кукла Чъки.",
                "annabelle": f"Хорър филм от {year} година за проклета кукла.",
                "the nun": f"Хорър филм от {year} година за демонична монахиня.",
                "lights out": f"Хорър филм от {year} година за създание, което живее в тъмнината.",
                "don't breathe": f"Трилър от {year} година за слеп мъж и крадци в неговия дом.",
                "get out": f"Психологически трилър от {year} година за расизъм и хипноза.",
                "us": f"Хорър трилър от {year} година за семейство и техните двойници.",
                "hereditary": f"Хорър филм от {year} година за семейни тайни и окултизъм.",
                "midsommar": f"Хорър филм от {year} година за скандинавски фестивал и ритуали.",
                "the witch": f"Хорър филм от {year} година за вещица в колониална Америка.",
                "the babadook": f"Психологически хорър от {year} година за майка, дете и чудовище.",
                "it follows": f"Хорър филм от {year} година за проклятие, което те преследва.",
                "a quiet place": f"Хорър трилър от {year} година за семейство в свят на тишина.",
                "bird box": f"Постапокалиптичен трилър от {year} година за свят, където не можеш да гледаш.",
                "the platform": f"Научнофантастичен трилър от {year} година за социална йерархия.",
                "parasite": f"Трилър драма от {year} година за класови различия в Корея.",
                "joker": f"Психологическа драма от {year} година за произхода на злодея Жокера.",
                "braveheart": f"Историческа драма от {year} година за Уилям Уолъс и шотландската свобода.",
                "gladiator": f"Историческа драма от {year} година за римски генерал, станал гладиатор.",
                "troy": f"Епическа драма от {year} година за Троянската война.",
                "300": f"Екшън филм от {year} година за 300-те спартанци в Термопилите.",
                "alexander": f"Биографична драма от {year} година за Александър Македонски.",
                "kingdom of heaven": f"Историческа драма от {year} година за кръстоносните походи.",
                "the last samurai": f"Историческа драма от {year} година за американски офицер в Япония.",
                "apocalypto": f"Историческа драма от {year} година за цивилизацията на маите.",
                "anime": f"Японски анимационен филм от {year} година.",
                "manga": f"Филм от {year} година, базиран на японска манга.",
                "dragon ball": f"Анимационен филм от {year} година от поредицата Драгън Бол.",
                "naruto": f"Анимационен филм от {year} година от поредицата Наруто.",
                "one piece": f"Анимационен филм от {year} година от поредицата Уан Пийс.",
                "attack on titan": f"Анимационен филм от {year} година за титаните.",
                "death note": f"Трилър от {year} година за тетрадка на смъртта.",
                "fullmetal alchemist": f"Фентъзи филм от {year} година за алхимия.",
                "ghost in the shell": f"Научнофантастичен филм от {year} година за киборги.",
                "akira": f"Научнофантастичен анимационен филм от {year} година.",
                "spirited away": f"Фентъзи анимационен филм от {year} година на Хаяо Миядзаки.",
                "princess mononoke": f"Фентъзи анимационен филм от {year} година за природата.",
                "my neighbor totoro": f"Семеен анимационен филм от {year} година за горски духове.",
                "castle in the sky": f"Приключенски анимационен филм от {year} година.",
                "howl's moving castle": f"Фентъзи анимационен филм от {year} година за магия.",
                "your name": f"Романтичен анимационен филм от {year} година за размяна на тела.",
                "weathering with you": f"Романтичен анимационен филм от {year} година за времето.",
                "demon slayer": f"Анимационен екшън от {year} година за ловци на демони.",
                "jujutsu kaisen": f"Анимационен екшън от {year} година за проклятия.",
                "my hero academia": f"Супергеройски анимационен филм от {year} година.",
                "one punch man": f"Супергеройска анимационна комедия от {year} година.",
                "hunter x hunter": f"Приключенски анимационен филм от {year} година.",
                "bleach": f"Свръхестествен анимационен екшън от {year} година.",
                "tokyo ghoul": f"Хорър анимационен филм от {year} година за гулове.",
                "parasyte": f"Хорър научнофантастичен анимационен филм от {year} година.",
                "cowboy bebop": f"Космически уестърн анимационен филм от {year} година.",
                "samurai champloo": f"Исторически анимационен филм от {year} година за самураи.",
                "vampire hunter d": f"Хорър анимационен филм от {year} година за ловец на вампири.",
                "neon genesis evangelion": f"Научнофантастичен анимационен филм от {year} година за меха."
            }
            
            # Check for matches in Bulgarian database
            for key, description in known_movies_bg.items():
                if key in title_lower:
                    return description
        
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
        
        # Generic fallback descriptions
        if language == "bulgarian":
            return f"Филм от {year} година."
        else:
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