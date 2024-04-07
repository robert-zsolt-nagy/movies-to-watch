from typing import Optional


class MovieRepository:

    def get_details_by_id(self, movie_id: int) -> dict:
        """
        Get the details of a movie with the given ID.

        Args:
            movie_id (int): The ID of the movie for which we need the movie details.

        Returns:
            dict: The details of the movie.
        """
        pass

    def get_trailer(self, movie_id: int) -> str:
        """
        Get the trailer URL for a movie with the given ID.

        Args:
            movie_id (int): The ID of the movie for which we need the trailer.

        Returns:
            str: The URL of the trailer.
        """
        pass

    def get_watch_providers(self, movie_id: int) -> Optional[dict]:
        """
        Get the watch providers for a specific movie.

        Args:
            movie_id (int): The ID of the movie for which to retrieve watch providers.

        Returns:
            Optional[dict]: A dictionary containing the watch providers for the specified movie if available.
        """
        pass
