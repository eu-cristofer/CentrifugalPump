# Example pump catalogue

`*.pumpcurve.json` files, one pump curve each, read by `pump.catalogue.Catalogue.from_folder`
and by the **Pump Selection** node (UC-01).  They are generated from the shipped
`.pumpflow` projects:

```bash
python examples/catalogue/build_catalogue.py
