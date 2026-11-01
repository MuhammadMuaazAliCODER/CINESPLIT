import { useEffect, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowLeft,
  faArrowRight,
  faMagnifyingGlass,
} from "@fortawesome/free-solid-svg-icons";
import MovieGrid from "../components/MovieGrid.jsx";
import { getMovieGenres, getMovies } from "../services/movies.js";
import DiscoveryShelves from "../components/DiscoveryShelves.jsx";
import ContinueWatching from "../components/ContinueWatching.jsx";
import SeoHead from "../components/SeoHead.jsx";

const initialPage = { results: [], page: 1, page_size: 20, total: 0, pages: 0 };

export default function MovieCatalogPage() {
  const [pageData, setPageData] = useState(initialPage);
  const [genres, setGenres] = useState([]);
  const [searchText, setSearchText] = useState("");
  const [filters, setFilters] = useState({
    search: "",
    genre: "",
    release_year: "",
    language: "",
    content_rating: "",
    sort: "-release_year",
    page: 1,
    page_size: 20,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const params = { ...filters };
    for (const key of ["search", "genre", "release_year", "language", "content_rating"]) {
      if (params[key] === "") delete params[key];
    }
    getMovies(params, { signal: controller.signal })
      .then(({ data }) => {
        if (active) setPageData(data);
      })
      .catch((requestError) => {
        if (active && requestError.name !== "CanceledError")
          setError(
            requestError.response?.data?.detail ||
              "The catalog could not be loaded. Try again shortly.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [filters]);

  useEffect(() => {
    const controller = new AbortController();
    getMovieGenres({ signal: controller.signal })
      .then(({ data }) => setGenres(data.genres))
      .catch(() => {});
    return () => controller.abort();
  }, []);

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value, page: 1 }));
  }

  function search(event) {
    event.preventDefault();
    updateFilter("search", searchText.trim());
  }

  return (
    <section className="catalog-page" aria-labelledby="catalog-title">
      <SeoHead title="Films to discover | CineSplit" description="Explore published films on CineSplit. Search films by genre, year, language, and rating." path="/" />
      <div className="catalog-hero">
        <div>
          <span className="eyebrow">THE CINESPLIT COLLECTION</span>
          <h1 id="catalog-title">Stories worth staying in for.</h1>
          <p>
            Find your next favorite across a hand-curated collection of films.
          </p>
        </div>
      </div>
      <ContinueWatching />
      <DiscoveryShelves />

      <form className="catalog-toolbar" onSubmit={search} role="search">
        <label className="catalog-search">
          <span className="sr-only">Search movie titles</span>
          <FontAwesomeIcon icon={faMagnifyingGlass} aria-hidden="true" />
          <input
            type="search"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="Search films"
          />
        </label>
        <label>
          <span className="sr-only">Genre</span>
          <input
            list="movie-genres"
            value={filters.genre}
            onChange={(event) => updateFilter("genre", event.target.value)}
            placeholder="All genres"
          />
          <datalist id="movie-genres">
            {genres.map((genre) => (
              <option key={genre} value={genre} />
            ))}
          </datalist>
        </label>
        <label>
          <span className="sr-only">Release year</span>
          <input
            type="number"
            min="1870"
            max="2100"
            value={filters.release_year}
            onChange={(event) =>
              updateFilter("release_year", event.target.value)
            }
            placeholder="Year"
          />
        </label>
        <label>
          <span className="sr-only">Original language</span>
          <input
            value={filters.language}
            onChange={(event) => updateFilter("language", event.target.value)}
            placeholder="Language"
          />
        </label>
        <label>
          <span className="sr-only">Content rating</span>
          <select
            value={filters.content_rating}
            onChange={(event) =>
              updateFilter("content_rating", event.target.value)
            }
          >
            <option value="">All ratings</option>
            {[
              "G",
              "PG",
              "PG-13",
              "R",
              "NC-17",
              "TV-G",
              "TV-PG",
              "TV-14",
              "TV-MA",
              "NR",
            ].map((rating) => (
              <option key={rating}>{rating}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="sr-only">Sort movies</span>
          <select
            value={filters.sort}
            onChange={(event) => updateFilter("sort", event.target.value)}
          >
            <option value="-release_year">Newest release</option>
            <option value="release_year">Oldest release</option>
            <option value="title">Title A–Z</option>
            <option value="-title">Title Z–A</option>
          </select>
        </label>
      </form>

      <div className="catalog-results-heading">
        <span>
          {loading
            ? "Loading films…"
            : `${pageData.total} ${pageData.total === 1 ? "film" : "films"}`}
        </span>
        <span>Curated for the big-screen feeling</span>
      </div>
      <MovieGrid movies={pageData.results} loading={loading} error={error} />
      {pageData.pages > 1 && (
        <nav className="movie-pagination" aria-label="Movie pages">
          <button
            type="button"
            className="quiet-button"
            disabled={loading || filters.page <= 1}
            onClick={() => updateFilter("page", filters.page - 1)}
          >
            <FontAwesomeIcon icon={faArrowLeft} aria-hidden="true" /> Previous
          </button>
          <span>
            Page {pageData.page} of {pageData.pages}
          </span>
          <button
            type="button"
            className="quiet-button"
            disabled={loading || filters.page >= pageData.pages}
            onClick={() => updateFilter("page", filters.page + 1)}
          >
            Next <FontAwesomeIcon icon={faArrowRight} aria-hidden="true" />
          </button>
        </nav>
      )}
    </section>
  );
}
