/****************************************************************************
** Meta object code from reading C++ file 'PBox.h'
**
** Created by: The Qt Meta Object Compiler version 67 (Qt 5.9.7)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "PBox.h"
#include <QtCore/qbytearray.h>
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'PBox.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 67
#error "This file was generated using the moc from 5.9.7. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

QT_BEGIN_MOC_NAMESPACE
QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
struct qt_meta_stringdata_PBox_t {
    QByteArrayData data[17];
    char stringdata0[176];
};
#define QT_MOC_LITERAL(idx, ofs, len) \
    Q_STATIC_BYTE_ARRAY_DATA_HEADER_INITIALIZER_WITH_OFFSET(len, \
    qptrdiff(offsetof(qt_meta_stringdata_PBox_t, stringdata0) + ofs \
        - idx * sizeof(QByteArrayData)) \
    )
static const qt_meta_stringdata_PBox_t qt_meta_stringdata_PBox = {
    {
QT_MOC_LITERAL(0, 0, 4), // "PBox"
QT_MOC_LITERAL(1, 5, 11), // "textChanged"
QT_MOC_LITERAL(2, 17, 0), // ""
QT_MOC_LITERAL(3, 18, 9), // "activated"
QT_MOC_LITERAL(4, 28, 8), // "newChild"
QT_MOC_LITERAL(5, 37, 18), // "PAbstractDataItem*"
QT_MOC_LITERAL(6, 56, 4), // "padi"
QT_MOC_LITERAL(7, 61, 11), // "setBoxTitle"
QT_MOC_LITERAL(8, 73, 8), // "boxTitle"
QT_MOC_LITERAL(9, 82, 5), // "force"
QT_MOC_LITERAL(10, 88, 8), // "gdUpdate"
QT_MOC_LITERAL(11, 97, 17), // "GetData::Dirfile*"
QT_MOC_LITERAL(12, 115, 7), // "dirFile"
QT_MOC_LITERAL(13, 123, 11), // "lastNFrames"
QT_MOC_LITERAL(14, 135, 8), // "activate"
QT_MOC_LITERAL(15, 144, 20), // "checkActivationState"
QT_MOC_LITERAL(16, 165, 10) // "styleLogic"

    },
    "PBox\0textChanged\0\0activated\0newChild\0"
    "PAbstractDataItem*\0padi\0setBoxTitle\0"
    "boxTitle\0force\0gdUpdate\0GetData::Dirfile*\0"
    "dirFile\0lastNFrames\0activate\0"
    "checkActivationState\0styleLogic"
};
#undef QT_MOC_LITERAL

static const uint qt_meta_data_PBox[] = {

 // content:
       7,       // revision
       0,       // classname
       0,    0, // classinfo
       9,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       3,       // signalCount

 // signals: name, argc, parameters, tag, flags
       1,    1,   59,    2, 0x06 /* Public */,
       3,    0,   62,    2, 0x06 /* Public */,
       4,    1,   63,    2, 0x06 /* Public */,

 // slots: name, argc, parameters, tag, flags
       7,    2,   66,    2, 0x0a /* Public */,
       7,    1,   71,    2, 0x2a /* Public | MethodCloned */,
      10,    2,   74,    2, 0x0a /* Public */,
      14,    0,   79,    2, 0x0a /* Public */,
      15,    0,   80,    2, 0x0a /* Public */,
      16,    0,   81,    2, 0x0a /* Public */,

 // signals: parameters
    QMetaType::Void, QMetaType::QString,    2,
    QMetaType::Void,
    QMetaType::Void, 0x80000000 | 5,    6,

 // slots: parameters
    QMetaType::Void, QMetaType::QString, QMetaType::Bool,    8,    9,
    QMetaType::Void, QMetaType::QString,    8,
    QMetaType::Void, 0x80000000 | 11, QMetaType::Int,   12,   13,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

       0        // eod
};

void PBox::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        PBox *_t = static_cast<PBox *>(_o);
        Q_UNUSED(_t)
        switch (_id) {
        case 0: _t->textChanged((*reinterpret_cast< QString(*)>(_a[1]))); break;
        case 1: _t->activated(); break;
        case 2: _t->newChild((*reinterpret_cast< PAbstractDataItem*(*)>(_a[1]))); break;
        case 3: _t->setBoxTitle((*reinterpret_cast< const QString(*)>(_a[1])),(*reinterpret_cast< bool(*)>(_a[2]))); break;
        case 4: _t->setBoxTitle((*reinterpret_cast< const QString(*)>(_a[1]))); break;
        case 5: _t->gdUpdate((*reinterpret_cast< GetData::Dirfile*(*)>(_a[1])),(*reinterpret_cast< int(*)>(_a[2]))); break;
        case 6: _t->activate(); break;
        case 7: _t->checkActivationState(); break;
        case 8: _t->styleLogic(); break;
        default: ;
        }
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        switch (_id) {
        default: *reinterpret_cast<int*>(_a[0]) = -1; break;
        case 2:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<int*>(_a[0]) = -1; break;
            case 0:
                *reinterpret_cast<int*>(_a[0]) = qRegisterMetaType< PAbstractDataItem* >(); break;
            }
            break;
        }
    } else if (_c == QMetaObject::IndexOfMethod) {
        int *result = reinterpret_cast<int *>(_a[0]);
        {
            typedef void (PBox::*_t)(QString );
            if (*reinterpret_cast<_t *>(_a[1]) == static_cast<_t>(&PBox::textChanged)) {
                *result = 0;
                return;
            }
        }
        {
            typedef void (PBox::*_t)();
            if (*reinterpret_cast<_t *>(_a[1]) == static_cast<_t>(&PBox::activated)) {
                *result = 1;
                return;
            }
        }
        {
            typedef void (PBox::*_t)(PAbstractDataItem * );
            if (*reinterpret_cast<_t *>(_a[1]) == static_cast<_t>(&PBox::newChild)) {
                *result = 2;
                return;
            }
        }
    }
}

const QMetaObject PBox::staticMetaObject = {
    { &QFrame::staticMetaObject, qt_meta_stringdata_PBox.data,
      qt_meta_data_PBox,  qt_static_metacall, nullptr, nullptr}
};


const QMetaObject *PBox::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *PBox::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_PBox.stringdata0))
        return static_cast<void*>(this);
    if (!strcmp(_clname, "PObject"))
        return static_cast< PObject*>(this);
    return QFrame::qt_metacast(_clname);
}

int PBox::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QFrame::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 9)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 9;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 9)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 9;
    }
    return _id;
}

// SIGNAL 0
void PBox::textChanged(QString _t1)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 0, _a);
}

// SIGNAL 1
void PBox::activated()
{
    QMetaObject::activate(this, &staticMetaObject, 1, nullptr);
}

// SIGNAL 2
void PBox::newChild(PAbstractDataItem * _t1)
{
    void *_a[] = { nullptr, const_cast<void*>(reinterpret_cast<const void*>(&_t1)) };
    QMetaObject::activate(this, &staticMetaObject, 2, _a);
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
