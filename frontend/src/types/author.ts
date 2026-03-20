export interface Author {
  id: string;
  author: string;
  country: string;
  language: string;
  model: string;
  year?: string;
  target_audience?: string;
  style_prompt?: string;
  face?: string;
  imitation?: string;
  rhythms_style?: string;
  exclude_words?: string;
}
