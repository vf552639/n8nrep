export interface Author {
  id: string;
  author: string;
  country: string;
  language: string;
  bio?: string;
  co_short?: string;
  city?: string;
  imitation?: string;
  year?: string;
  face?: string;
  target_audience?: string;
  rhythms_style?: string;
  exclude_words?: string;
  usage_count?: number;
}

export type AuthorFormPayload = {
  author: string;
  country: string;
  language: string;
  bio: string;
  co_short: string;
  city: string;
  imitation: string;
  year: string;
  face: string;
  target_audience: string;
  rhythms_style: string;
  exclude_words: string;
};
