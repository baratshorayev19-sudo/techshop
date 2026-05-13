# TechShop Django Ecommerce Project

Professional diploma project: **Development of an Online Shop for Selling Household Appliances, Phones, and Computers**.

## Features

- Home, products, product detail, cart, checkout, about, and contact pages
- Session-based add to cart, update quantity, and remove item flow
- Product search, category filter, price filter, and sorting
- Checkout form validation
- Responsive modern UI with product ratings, badges, hero banner, and featured products
- SEO-friendly templates and reusable component-style partials

## Run locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Structure

- `TechShop/` - Django project settings and root URLs
- `shop/` - ecommerce app with product data, forms, views, URLs, and cart logic
- `templates/` - reusable Django templates and pages
- `static/css/styles.css` - complete responsive visual system
- `static/js/main.js` - mobile navigation and message animation

## Future Scalability Ideas

- Replace dummy product data with Django database models
- Add user accounts, order history, and admin product management
- Integrate Stripe, Payme, Click, or other payment providers
- Add inventory tracking, coupons, wishlists, and product reviews
- Add REST API endpoints and a React frontend if the project needs SPA behavior later
