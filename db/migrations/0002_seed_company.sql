INSERT INTO companies (name, website, notes)
VALUES ('Burgundy Asset Management', 'https://www.burgundyasset.com', 'Canadian value-oriented asset manager (Toronto), tracked for AUM, fund holdings, key personnel, and Korean equity exposure.')
ON CONFLICT (name) DO NOTHING;
