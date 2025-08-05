# migration_script.py
# Run this script to create the new database tables for learning paths

from app import app, db, LearningTopic
import json


def create_tables():
    """Create all database tables"""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")


def populate_sample_topics():
    """Add sample learning topics if they don't exist"""
    with app.app_context():
        if LearningTopic.query.count() == 0:
            topics = [
                ("Python Programlama",
                 "Python dilinde temel ve ileri seviye programlama konularını öğrenin. Veri yapıları, algoritma tasarımı ve modern Python tekniklerini kapsayan kapsamlı bir yol."),
                ("Web Geliştirme",
                 "HTML, CSS, JavaScript ile modern web uygulamaları geliştirmeyi öğrenin. Frontend ve backend teknolojileri ile tam yığın geliştirici olma yolculuğu."),
                ("Veri Bilimi",
                 "Veri analizi, makine öğrenmesi ve istatistiksel modelleme tekniklerini öğrenin. Python/R ile veri bilimi projelerinde uzmanlaşın."),
                ("Mobil Uygulama",
                 "iOS ve Android platformları için native ve cross-platform mobil uygulama geliştirme tekniklerini öğrenin."),
                ("Veritabanı Yönetimi",
                 "SQL ve NoSQL veritabanı sistemlerini öğrenin. Veri modelleme, optimizasyon ve büyük veri yönetimi konularında uzmanlaşın."),
                ("DevOps & Cloud",
                 "Deployment, CI/CD, container teknolojileri ve bulut mimarisi konularında expertise kazanın."),
                ("UI/UX Tasarım",
                 "Kullanıcı deneyimi tasarımı, arayüz geliştirme ve tasarım düşüncesi metodolojilerini öğrenin."),
                ("Yapay Zeka & ML",
                 "Machine Learning, Deep Learning ve yapay zeka uygulamaları geliştirme konularında uzmanlaşın."),
                ("Blockchain",
                 "Blockchain teknolojisi, kripto para sistemleri ve akıllı kontrat geliştirme konularını öğrenin."),
                ("Siber Güvenlik",
                 "Güvenlik testleri, penetrasyon testleri ve siber güvenlik risk yönetimi konularında uzmanlaşın."),
                ("Proje Yönetimi", "Agile, Scrum metodolojileri ve modern proje yönetimi tekniklerini öğrenin."),
                ("Grafik Tasarım",
                 "Adobe Creative Suite ve modern tasarım araçları ile profesyonel grafik tasarım teknikleri.")
            ]

            for name, desc in topics:
                topic = LearningTopic(name=name, description=desc)
                db.session.add(topic)

            db.session.commit()
            print(f"✅ {len(topics)} sample learning topics added!")
        else:
            print("ℹ️  Learning topics already exist, skipping sample data.")


if __name__ == '__main__':
    create_tables()
    populate_sample_topics()
    print("🎉 Migration completed successfully!")