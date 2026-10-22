"""Offline regressions: legacy VI links, new slugs and EN are protected."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vi_excel_url_cleanup import migrations, rewrite_known_links

SITE='https://blog.rentbikehanoi.com'


class MigrationTests(unittest.TestCase):
    def ledger(self):
        posts={}
        for n in range(168, 501):
            posts[str(n)]={'phase':'VERIFIED','status':'publish','wp_id':n+2000,
                'slug':f'excel-{n}-example-post-{n}',
                'url':f'{SITE}/excel-{n}-example-post-{n}/'}
        return {'posts': posts}

    def test_all_333_have_distinct_new_urls(self):
        m, ids=migrations(self.ledger())
        self.assertEqual(len(m),333)
        self.assertEqual(len(ids),333)
        self.assertEqual(len(set(m.values())),333)
        self.assertNotIn('excel-', next(iter(m.values())))

    def test_clean_link_and_untouched_other_html(self):
        m,_=migrations(self.ledger())
        a=f'<a href="{SITE}/excel-168-example-post-168/">VI</a>'
        b=f'<a href="{SITE}/en/english-page/">EN</a>'
        new,n=rewrite_known_links(a+b,m)
        self.assertEqual(n,1)
        self.assertIn(f'{SITE}/example-post-168/',new)
        self.assertIn(b,new)
        twice,z=rewrite_known_links(new,m)
        self.assertEqual(z,0)
        self.assertEqual(twice,new)

    def test_unknown_excel_link_blocks(self):
        m,_=migrations(self.ledger())
        with self.assertRaisesRegex(RuntimeError,'Unregistered'):
            rewrite_known_links(f'{SITE}/excel-999-unknown/',m)

    def test_bad_ledger_fails_closed(self):
        d=self.ledger()
        d['posts']['168']['phase']='POST_INTENT'
        with self.assertRaisesRegex(RuntimeError,'VERIFIED'):
            migrations(d)

if __name__=='__main__':
    unittest.main()
