import openai
import os
import logging
from tqdm import tqdm
import trustllm.config
from trustllm.utils import file_process
from tenacity import retry, wait_random_exponential, stop_after_attempt


class DataEmbedder:
    def __init__(self, save_dir='saved_embeddings'):
        """
        Initialize the DataEmbedder class.

        Args:
        - save_dir (str): Directory where the embeddings will be saved.
        """
        self.save_dir = save_dir
        # Create the directory if it does not exist
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        openai.api_key = trustllm.config.openai_key

    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(6))
    def get_embeddings(self, string):
        """
        Function to get embeddings from OpenAI's Embedding API.

        Args:
        - string (str): The input string for which the embedding is required.

        Returns:
        - Embeddings response from the API.
        """
        response = openai.Embedding.create(
            model='text-embedding-ada-002',  # Example model
            input=string
        )
        return response["data"][0]["embedding"]

    def save_embeddings(self, embeddings, filename):
        """
        Save the embeddings to a file.

        Args:
        - embeddings (list): The embeddings to be saved.
        - filename (str): The filename to save the embeddings.
        """
        save_path = os.path.join(self.save_dir, filename)
        file_process.save_json(embeddings, save_path)
        logging.info("Embeddings saved to %s", save_path)

    def embed_data(self, data, filename='embeddings.json', resume=False):
        """
        Embed the given data and save it.

        Args:
        - data (list): The data to be embedded.
        - filename (str): The filename to save the embeddings.
        - resume (bool): Flag to indicate whether to resume from saved progress.
        """
        assert isinstance(data, list), "Data must be a list."
        print('Evaluating...')
        # If resume is True, attempt to load previous progress
        if resume:
            try:
                data = file_process.load_json(os.path.join(self.save_dir, filename))
                logging.info("Resuming from saved progress.")
            except FileNotFoundError:
                logging.warning("No saved progress file found. Starting from scratch.")

        for el in tqdm(data):
            try:
                if 'embedding' not in el:
                    el['embedding'] = self.get_embeddings(el['res'])
                    logging.info("Evaluated item: %s", el.get('res', ''))
            except Exception as e:
                logging.error("Error embedding item %s: %s", el.get('res', ''), str(e))
                # Save current progress before raising the exception
                self.save_embeddings(data, filename)
                raise  # Re-raise the exception to notify the caller

        # Save the final embeddings
        self.save_embeddings(data, filename)

        # return save path
        return os.path.join(self.save_dir, filename)
