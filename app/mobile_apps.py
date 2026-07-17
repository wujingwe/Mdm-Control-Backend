class MobileApp(Base):
    __tablename__ = "mobile_apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  
