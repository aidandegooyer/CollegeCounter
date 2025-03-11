import {defineField, defineType} from 'sanity'

export const postType = defineType({
  name: 'post',
  title: 'Post',
  type: 'document',
  fields: [
    defineField({
      name: 'title',
      type: 'string',
      validation: (rule) => rule.required(),
    }),
    defineField({
      name: 'slug',
      type: 'slug',
      options: {source: 'title'},
      validation: (rule) => rule.required(),
    }),
    defineField({
        name: 'author',
        type: 'string',
        validation: (rule) => rule.required(),
      }),
      defineField({
        name: 'authorLink',
        type: 'string',
      }),
    defineField({
      name: 'publishedAt',
      type: 'datetime',
      initialValue: () => new Date().toISOString(),
      validation: (rule) => rule.required(),
    }),
    defineField({
      name: 'image',
      type: 'image',
    }),
    defineField({
      name: 'body',
      type: 'array',
      of: [{type: 'block'},
        {
          type: 'image',
          options: {hotspot: true},
          // Optionally, you can add additional fields for captions, alt text, etc.
          fields: [
            {
              name: 'caption',
              type: 'string',
              options: {isHighlighted: true}, // makes this field easily accessible
            },
            {
              name: 'alt',
              type: 'string',
            },
          ],
        },
      ],
    }),
  ],
})