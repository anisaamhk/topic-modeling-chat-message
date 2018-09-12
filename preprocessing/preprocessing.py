import time
import logging
from multiprocessing import cpu_count

from flashtext.keyword import KeywordProcessor
from spacy.lang.id import Indonesian
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

from preprocessing.utils import PreprocessingUtils, PreprocessingUtilsV2
from utils import constant
from repository.repository import Repository

logger = logging.getLogger("goliath")


class Preprocessing(object):
    def __init__(self):
        # init NLP
        self.nlp = Indonesian()

        # init flash text
        self.keyword_processor_slang_word = KeywordProcessor()
        self.keyword_processor_emoticon = KeywordProcessor()

        # init stemmer
        self.stemmer = StemmerFactory().create_stemmer()

        self.__init_flash_text_corpus()
        self.__init_custom_stop_word()

    def __init_flash_text_corpus(self):
        """ Init flash text corpus. """
        # build slang word corpus
        slang_words_raw = Repository.get_slang_word()
        for word in slang_words_raw.values:
            self.keyword_processor_slang_word.add_keyword(word[0], word[1])

        # build emoticon corpus
        emoticon_raw = constant.EMOTICON_LIST
        for key, values in emoticon_raw:
            for value in values:
                self.keyword_processor_emoticon.add_keyword(value, key)

    def __init_custom_stop_word(self):
        """ Custom stop word for chat message content. """

        for stop_word in constant.STOP_WORD:
            self.nlp.vocab[stop_word].is_stop = True

        for stop_word in constant.EXC_STOP_WORD:
            self.nlp.vocab[stop_word].is_stop = False

    def cleaning(self, chat_message_list):
        """
        Pre-processing the content from ChatMessage.

        :param chat_message_list: dirty content from list of ChatMessage.
        :return: list of ChatMessage.
        """
        chat_message_list_temp = []

        if chat_message_list:
            logger.info('Pre-processing started...')
            start_time = time.time()

            for chat_message in chat_message_list:
                content = self.__preprocessing_flow(chat_message.content)
                chat_message.content = content
                if content.strip():
                    chat_message_list_temp.append(chat_message)

            logger.info(f'Pre-processing finished. {time.time() - start_time} seconds')
        else:
            logger.info('No chat message yet.')

        return chat_message_list_temp

    def cleaning_with_pipe(self, chat_message_list):
        """
        [DEPRECATED]
        Pre-processing the content from ChatMessage with multi threading from spaCy.

        :param chat_message_list: dirty content from list of ChatMessage.
        :return: list of ChatMessage.
        """

        if chat_message_list:
            logger.info('Pre-processing started...')
            start_time = time.time()
            index = 0

            chat_content_list = [chat_message.content for chat_message in chat_message_list]
            for content in self.nlp.pipe(chat_content_list, n_threads=cpu_count()):
                chat_message_list[index].content = self.__preprocessing_flow(content.text)
                index = index + 1

            logger.info(f'Pre-processing finished. {time.time() - start_time} seconds')
        else:
            logger.info('No chat message yet.')

        return chat_message_list

    def __preprocessing_flow(self, content):
        """ Preprocessing flow. """
        # normalize emoticon
        # content = PreprocessingUtilsV2.normalize_emoticon(content, self.keyword_processor_emoticon)

        content = str(content)

        # normalize url
        content = PreprocessingUtils.normalize_url(content)

        # remove url
        content = PreprocessingUtils.remove_url(content)

        # remove email
        content = PreprocessingUtils.remove_email(content)

        # remove digit number
        content = PreprocessingUtils.remove_digit_number(content)

        # case folding lower case
        content = PreprocessingUtils.case_folding_lowercase(content)

        # remove punctuation
        content = PreprocessingUtils.remove_punctuation(content)

        # normalize slang word
        content = PreprocessingUtilsV2.normalize_slang_word(content, self.keyword_processor_slang_word)

        # stemming, tokenize, remove stop word
        content = PreprocessingUtils.stemming_tokenize_and_remove_stop_word(content, self.nlp, self.stemmer)

        # remove unused character
        content = PreprocessingUtils.remove_unused_character(content)

        # join negation word
        content = PreprocessingUtils.join_negation(content)

        # remove extra space between word
        content = PreprocessingUtils.removing_extra_space(content)

        # TODO add another pre-processing if needed

        return content
