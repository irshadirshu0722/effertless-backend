# Innotter API

This document describes the HTTP API exposed by the Innotter service.

## General information

- **\*\*Base URL:\*\*** the URL where this Django service is deployed.

- **\*\*Format:\*\*** JSON responses use `Content-Type: application/json`.

- **\*\*Authentication:\*\*** every endpoint requires an active user. Send a JWT in the

`Authorization` header:

```http

Authorization: Bearer <jwt-token>

```

- Requests with no credentials return `401 Unauthorized`. An invalid bearer

token also returns `401 Unauthorized`.

- Validation errors return `400 Bad Request` and are returned as an object whose

keys identify the invalid fields.

- Numeric pagination parameters must be positive integers (`>= 1`).

- Dates are formatted as `YYYY-MM-DD`; timestamps are ISO 8601 values in UTC.

- Rate limits are listed for each endpoint. Exceeding a limit is handled by the

configured REST framework throttle.

- The service uses trailing slashes for page and tag routes. The feed and post

routes are defined without a trailing slash.

Unless stated otherwise, examples use:

```http

Host: api.example.com

Authorization: Bearer <jwt-token>

```

## Shared response objects

### Tag

```json

{

"id": 12,

"name": "engineering"

}

```

### Page

```json

{

"id": 42,

"name": "Engineering",

"description": "A page for engineering discussions.",

"user_id": "550e8400-e29b-41d4-a716-446655440000",

"image_url": "https://cdn.example.com/pages/42.png",

"tags": [

{

"id": 12,

"name": "engineering"

}

],

"is_blocked": false,

"unblock_date": null,

"created_at": "2026-10-08T10:30:00Z",

"updated_at": "2026-10-08T10:30:00Z"

}

```

### Post

Posts include `reply_to` and `replies`. These fields can be `null` or an empty

array when there is no reply relationship. `likes` and `total_likes` are

included when the service has loaded them.

```json

{

"id": 101,

"page_id": 42,

"content": "Welcome to the engineering page.",

"page": null,

"reply_to_id": null,

"reply_to": null,

"replies": [],

"likes": [],

"total_likes": 0,

"created_at": "2026-10-08T10:35:00Z",

"updated_at": "2026-10-08T10:35:00Z"

}

```

## Tags

### List tags

```http

GET /tags/

```

Lists tags ordered and paginated by the tag service.

#### Query parameters

| Parameter | Required | Default | Description |

| --- | --- | --- | --- |

| `page` | No | `1` | One-based page number. Must be positive. |

| `limit` | No | `10` | Number of tags to request. Must be positive. |

| `filter_by_name` | No | none | Filters tags by name. |

#### Request body and content type

No request body. Do not send a `Content-Type` header unless the client requires

one.

#### Success response: `200 OK`

```json

[

{

"id": 12,

"name": "engineering"

},

{

"id": 13,

"name": "python"

}

]

```

### Create a tag

```http

POST /tag/

Content-Type: application/json

```

#### Request body

| Field | Required | Type | Constraints |

| --- | --- | --- | --- |

| `name` | Yes | string | 1-20 characters |

```json

{

"name": "python"

}

```

#### Success response: `201 Created`

```json

{

"id": 13,

"name": "python"

}

```

Duplicate tag names or invalid fields return `400 Bad Request`.

## Pages

### List pages

```http
GET /pages/
```

Returns a paginated list of pages. By default, the endpoint does not filter pages by owner. Use `my_pages=true` to return only pages owned by the authenticated user.

#### Query parameters

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `page` | No | `1` | One-based page number. Must be a positive integer. |
| `limit` | No | `10` | Number of pages to return. Must be a positive integer. |
| `filter_by_title` | No | none | Case-insensitive search across page name and description. |
| `my_pages` | No | `false` | When `true`, returns only pages owned by the authenticated user. When omitted or `false`, does not apply an owner filter. |

#### Request body

No request body.

#### Success response: `200 OK`

```json
{
  "items": [
    {
      "id": 42,
      "name": "Engineering",
      "description": "A page for engineering discussions.",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "image_url": "https://cdn.example.com/pages/42.png",
      "tags": [
        {
          "id": 12,
          "name": "engineering"
        }
      ],
      "is_blocked": false,
      "unblock_date": null,
      "created_at": "2026-10-08T10:30:00Z",
      "updated_at": "2026-10-08T10:30:00Z"
    }
  ],
  "has_next": true,
  "has_prev": false,
  "total_items": 21,
  "total_pages": 3,
  "page": 1,
  "limit": 10
}
```

The `items` array contains page objects. `has_next` and `has_prev` indicate whether another page exists in the corresponding direction. `total_items` and `total_pages` describe the filtered result set.

#### Examples

```http
GET /pages/?my_pages=true
GET /pages/?page=2&limit=5
GET /pages/?filter_by_title=python
GET /pages/?my_pages=true&filter_by_title=python&page=1&limit=10
```

Invalid or non-positive `page` and `limit` values return `400 Bad Request`.


### Create a page

```http

POST /page/

Content-Type: multipart/form-data

```

The image must be sent as an uploaded image file. JSON is not accepted for this

endpoint because the image is read from the multipart upload.

#### Form fields

| Field | Required | Type | Constraints |

| --- | --- | --- | --- |

| `image` | Yes | image file | Must be a valid image |

| `name` | Yes | string | Maximum 100 characters |

| `description` | Yes | string | Text |

| `tags` | No | array of strings | Each tag is at most 50 characters |

Example multipart form:

```text

image: page.png

name: Engineering

description: A page for engineering discussions.

tags: engineering

tags: python

```

#### Success response: `201 Created`

Returns a [Page](#page) object.

```json

{

"id": 42,

"name": "Engineering",

"description": "A page for engineering discussions.",

"user_id": "550e8400-e29b-41d4-a716-446655440000",

"image_url": "https://cdn.example.com/pages/42.png",

"tags": [

{

"id": 12,

"name": "engineering"

},

{

"id": 13,

"name": "python"

}

],

"is_blocked": false,

"unblock_date": null,

"created_at": "2026-10-08T10:30:00Z",

"updated_at": "2026-10-08T10:30:00Z"

}

```

### Get a page and its posts

```http

GET /page/{page_id}/

```

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `page_id` | Yes | Numeric page ID |

#### Query parameters

| Parameter | Required | Default | Description |

| --- | --- | --- | --- |

| `page` | No | `1` | One-based post page number. Must be positive. |

| `limit` | No | `30` | Number of posts per page. Must be positive. |

#### Request body and content type

No request body.

#### Success response: `200 OK`

```json

{

"page": {

"id": 42,

"name": "Engineering",

"description": "A page for engineering discussions.",

"user_id": "550e8400-e29b-41d4-a716-446655440000",

"image_url": "https://cdn.example.com/pages/42.png",

"tags": [

{

"id": 12,

"name": "engineering"

}

],

"is_blocked": false,

"unblock_date": null,

"created_at": "2026-10-08T10:30:00Z",

"updated_at": "2026-10-08T10:30:00Z"

},

"posts": [],

"has_next": false,

"has_prev": false,

"total_items": 0,

"total_pages": 0,

"current_page": 1,

"limit": 30

}

```

Returns `404 Not Found` when the page does not exist.

### Update a page

```http

PATCH /page/{page_id}/

Content-Type: multipart/form-data

```

The page owner can update the page. All fields are optional, but at least one

field should be provided. Use multipart form data when changing `image`.

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `page_id` | Yes | Numeric page ID |

#### Form fields

| Field | Required | Type | Constraints |

| --- | --- | --- | --- |

| `image` | No | image file | Must be a valid image |

| `name` | No | string | Maximum 100 characters |

| `description` | No | string | Text |

| `new_tags` | No | array of strings | Each tag is at most 50 characters |

| `deleted_tags` | No | array of strings | Each tag is at most 50 characters |

#### Success response: `200 OK`

Returns the updated [Page](#page) object.

Common error responses are `403 Forbidden` for a non-owner and `404 Not Found`

for a missing page.

### Delete a page

```http

DELETE /page/{page_id}/

```

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `page_id` | Yes | Numeric page ID |

#### Request body and content type

No request body.

#### Success response: `200 OK`

```json

{

"message": "Page deleted successfully"

}

```

Non-owners receive `403 Forbidden`; a missing page returns `404 Not Found`.

### Follow a page

```http

PATCH /page/{page_id}/follow/

```

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `page_id` | Yes | Numeric page ID |

#### Request body and content type

No request body.

#### Success response: `200 OK`

```json

{

"id": 501,

"page_id": 42,

"user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

}

```

You cannot follow your own page. Following a page more than once also fails;

both cases return `406 Not Acceptable`. A missing page returns `404 Not Found`.

### Unfollow a page

```http

PATCH /page/{page_id}/unfollow/

```

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `page_id` | Yes | Numeric page ID |

#### Request body and content type

No request body.

#### Success response: `200 OK`

```json

{

"message": "Successfully unfollowed this page"

}

```

If the current user is not following the page, the service returns

`404 Not Found`.

### Block a page

```http

PATCH /page/{page_id}/block/

Content-Type: application/json

```

This operation is restricted to admins and moderators whose group matches the

page owner's group.

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `page_id` | Yes | Numeric page ID |

#### Request body

| Field | Required | Type | Format |

| --- | --- | --- | --- |

| `unblock_date` | Yes | string | `YYYY-MM-DD` |

```json

{

"unblock_date": "2026-10-31"

}

```

#### Success response: `200 OK`

Returns the updated [Page](#page), with `is_blocked` set to `true` and

`unblock_date` set to the requested date.

Unauthorized page-management attempts return `403 Forbidden`; a missing page

returns `404 Not Found`.

### List page followers

```http

GET /page/{page_id}/followers/

```

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `page_id` | Yes | Numeric page ID |

#### Request body and content type

No request body.

#### Success response: `200 OK`

```json

[

{

"id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",

"image_url": "https://cdn.example.com/users/7.png",

"group_id": 3,

"username": "alex"

}

]

```

An empty follower list is returned as `[]`. Access is allowed for the page

owner, admins, and moderators whose group matches the page owner's group.

Access to a missing or restricted page returns `404 Not Found` or `403

Forbidden`, respectively.

## Posts

### Create a post

```http

POST /post/{page_id}/post

Content-Type: application/json

```

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `page_id` | Yes | Numeric page ID |

#### Request body

| Field | Required | Type | Constraints |

| --- | --- | --- | --- |

| `content` | Yes | string | At least 1 character |

| `reply_to_id` | No | integer or `null` | Existing post ID to reply to |

```json

{

"content": "What are you working on today?",

"reply_to_id": null

}

```

#### Success response: `201 Created`

Returns a [Post](#post) object.

The page must exist and the current user must be allowed to post to it.

Otherwise the service returns `404 Not Found` or `403 Forbidden`. An invalid

`reply_to_id` returns `404 Not Found`; invalid body fields return `400 Bad

Request`.

### Get the post feed

```http

GET /feed

```

Returns a cursor-paginated feed for the current user.

#### Query parameters

| Parameter | Required | Default | Description |

| --- | --- | --- | --- |

| `cursor` | No | none | Cursor returned by the previous response |

| `limit` | No | `10` | Number of posts to request. Must be positive. |

#### Request body and content type

No request body.

#### Success response: `200 OK`

```json

{

"posts": [

{

"id": 101,

"page_id": 42,

"content": "Welcome to the engineering page.",

"page": null,

"reply_to_id": null,

"reply_to": null,

"replies": [],

"likes": [],

"total_likes": 0,

"created_at": "2026-10-08T10:35:00Z",

"updated_at": "2026-10-08T10:35:00Z"

}

],

"has_next": true,

"cursor": "eyJvZmZzZXQiOjEwfQ=="

}

```

Pass the returned `cursor` unchanged as the next request's `cursor` parameter.

The cursor is `null` when there is no next page.

### Update a post

```http

PATCH /post/{post_id}

Content-Type: application/json

```

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `post_id` | Yes | Numeric post ID |

#### Request body

| Field | Required | Type | Constraints |

| --- | --- | --- | --- |

| `content` | Yes | string | At least 1 character |

```json

{

"content": "Updated discussion text."

}

```

#### Success response: `200 OK`

Returns the updated [Post](#post) object.

Non-owners receive `403 Forbidden`; a missing post or its page returns

`404 Not Found`.

### Delete a post

```http

DELETE /post/{post_id}

```

#### Path parameters

| Parameter | Required | Description |

| --- | --- | --- |

| `post_id` | Yes | Numeric post ID |

#### Request body and content type

No request body.

#### Success response: `204 No Content`

The response has an empty body. A missing post or page returns `404 Not Found`;

a non-owner receives `403 Forbidden`.

## Common error response shapes

Validation errors normally identify the failing field:

```json

{

"content": [

"This field may not be blank."

]

}

```

Authentication errors are returned by Django REST framework:

```json

{

"detail": "Authentication credentials were not provided."

}

```

Service errors use the same `detail` field:

```json

{

"detail": "Page not found"

}

```

## Client implementation notes

1\. Treat IDs as integers except for user IDs, which are UUID strings.

2\. Do not assume that a post's `page`, `likes`, or timestamps are always

 populated; the serializer allows some nested and metadata fields to be

 absent or `null`.

3\. Use `PATCH` for follow, unfollow, block, and partial page/post changes.

4\. A successful post deletion is the only documented endpoint that returns

 `204`; do not try to parse a JSON body from that response.

5\. The page create and update endpoints require multipart encoding even when

 only text fields are being changed during an update if the client uses the

 image field.
